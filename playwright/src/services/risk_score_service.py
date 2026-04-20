"""
V3.4 RiskScore Service (Browser Side)
浏览器端风险评分服务 - 为Pipeline提供实时风险评估
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

class RiskScoreService:
    """
    浏览器端风险评分服务
    在Playwright环境中运行，提供即时风险评估
    """

    def __init__(self):
        self.base_threshold = 0.7
        self.min_threshold = 0.3
        self.max_threshold = 0.7

        self.consecutive_success = 0
        self.consecutive_fail = 0
        self.risk_history = []
        self.recent_ops_count = 0
        self.last_op_time = datetime.utcnow()

        self._lock = asyncio.Lock()

    def calculate_threshold(self) -> float:
        """
        根据连续成功次数动态计算阈值
        每连续成功3次，阈值降低0.1（更激进）
        """
        if self.consecutive_fail > 0:
            # 有失败时，回归基础阈值
            return self.base_threshold

        reduction = (self.consecutive_success // 3) * 0.1
        return max(self.base_threshold - reduction, self.min_threshold)

    def calculate_risk_score(self, context: dict) -> tuple[float, List[Dict[str, Any]]]:
        """
        计算当前操作的风险得分 (0.0 ~ 1.0)
        返回: (得分, 风险因素列表)
        """
        score = 0.0
        factors = []

        # 因素1: 页面类型 (0-0.3)
        page_type = context.get('page_type', 'unknown')
        page_type_scores = {
            'login': 0.3,
            'login_required': 0.3,
            'captcha': 0.25,
            'popup': 0.15,
            'job_detail': 0.1,
            'search': 0.05,
            'unknown': 0.05
        }
        page_score = page_type_scores.get(page_type, 0.05)
        if page_score > 0:
            score += page_score
            factors.append({
                "type": page_type,
                "weight": page_score,
                "source": "page_type"
            })

        # 因素2: 连续失败次数 (0-0.3)
        consecutive_fail = context.get('consecutive_fail', 0)
        fail_score = min(consecutive_fail * 0.1, 0.3)
        if fail_score > 0:
            score += fail_score
            factors.append({
                "type": "consecutive_fail",
                "weight": fail_score,
                "count": consecutive_fail
            })

        # 因素3: 操作频率 (0-0.2)
        recent_ops = context.get('recent_operations', 0)
        if recent_ops > 10:
            op_score = 0.2
            score += op_score
            factors.append({
                "type": "high_frequency",
                "weight": op_score,
                "ops": recent_ops
            })
        elif recent_ops > 5:
            op_score = 0.1
            score += op_score
            factors.append({
                "type": "medium_frequency",
                "weight": op_score,
                "ops": recent_ops
            })

        # 因素4: 异常关键词 (0-0.2)
        if context.get('has_error_keywords', False):
            score += 0.2
            factors.append({
                "type": "error_keywords",
                "weight": 0.2
            })

        # 因素5: 验证码 (0-0.25)
        if context.get('has_captcha', False):
            score += 0.25
            factors.append({
                "type": "captcha_detected",
                "weight": 0.25
            })

        # 因素6: URL跳转 (0-0.15)
        if context.get('url_redirected', False):
            score += 0.15
            factors.append({
                "type": "url_redirect",
                "weight": 0.15
            })

        # 因素7: 短时间内连续操作 (0-0.15)
        time_since_last_op = (datetime.utcnow() - self.last_op_time).total_seconds()
        if time_since_last_op < 5 and self.recent_ops_count > 3:
            score += 0.15
            factors.append({
                "type": "rapid_operations",
                "weight": 0.15,
                "seconds_since_last": time_since_last_op
            })

        final_score = min(score, 1.0)

        # 更新操作计数
        self._update_ops_count()

        return final_score, factors

    def _update_ops_count(self):
        """更新操作计数"""
        now = datetime.utcnow()
        if (now - self.last_op_time).total_seconds() < 60:
            self.recent_ops_count += 1
        else:
            self.recent_ops_count = 1
        self.last_op_time = now

    def evaluate_risk_level(self, score: float, threshold: float) -> tuple[str, str]:
        """
        评估风险等级和行动
        返回: (level, action)
        """
        if score > threshold:
            return "high", "human_intervention_required"
        elif score > threshold * 0.6:
            return "medium", "auto_recovery"
        else:
            return "low", "auto_continue"

    async def record_result(self, success: bool, risk_score: float = None, context: dict = None):
        """
        记录结果，更新连续成功/失败计数
        """
        async with self._lock:
            if success:
                self.consecutive_success += 1
                self.consecutive_fail = 0
            else:
                self.consecutive_fail += 1
                self.consecutive_success = 0

            # 记录历史
            self.risk_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "success": success,
                "risk_score": risk_score,
                "context": context
            })

            # 只保留最近50条记录
            if len(self.risk_history) > 50:
                self.risk_history = self.risk_history[-50:]

    def reset_state(self):
        """重置风险状态"""
        self.consecutive_success = 0
        self.consecutive_fail = 0
        self.risk_history = []
        self.recent_ops_count = 0

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "consecutive_success": self.consecutive_success,
            "consecutive_fail": self.consecutive_fail,
            "current_threshold": self.calculate_threshold(),
            "base_threshold": self.base_threshold,
            "min_threshold": self.min_threshold,
            "risk_history_count": len(self.risk_history),
            "recent_ops_count": self.recent_ops_count
        }

    def get_adaptive_threshold(self) -> float:
        """获取当前自适应阈值"""
        return self.calculate_threshold()


# 全局单例
risk_score_service = RiskScoreService()