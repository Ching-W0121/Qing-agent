"""
V3.4 RiskScore Engine
动态风险评分引擎 - 连续成功次数越多，阈值越低（越激进）
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

class RiskScoreEngine:
    """
    动态风险评分引擎
    连续成功次数越多，阈值越低（越激进）
    """

    def __init__(self):
        self.base_threshold = 0.7      # 基础阈值
        self.min_threshold = 0.3       # 最低阈值（最激进）
        self.consecutive_success = 0   # 连续成功计数
        self.consecutive_fail = 0      # 连续失败计数
        self.risk_history = []         # 历史风险记录
        self.recent_operations = 0     # 近期操作计数
        self.last_reset_time = datetime.utcnow()

    def calculate_threshold(self) -> float:
        """
        根据连续成功次数动态计算阈值
        每连续成功3次，阈值降低0.1
        """
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
            'login_required': 0.3,
            'captcha': 0.25,
            'popup': 0.15,
            'job_detail': 0.1,
            'unknown': 0.05
        }
        page_score = page_type_scores.get(page_type, 0.05)
        if page_score > 0:
            score += page_score
            factors.append({"type": page_type, "weight": page_score, "source": "page_type"})

        # 因素2: 连续失败次数 (0-0.3)
        consecutive_fail = context.get('consecutive_fail', 0)
        fail_score = min(consecutive_fail * 0.1, 0.3)
        if fail_score > 0:
            score += fail_score
            factors.append({"type": "consecutive_fail", "weight": fail_score, "count": consecutive_fail})

        # 因素3: 短时间内操作频率 (0-0.2)
        recent_ops = context.get('recent_operations', 0)
        if recent_ops > 10:
            op_score = 0.2
            score += op_score
            factors.append({"type": "high_frequency", "weight": op_score, "ops": recent_ops})
        elif recent_ops > 5:
            op_score = 0.1
            score += op_score
            factors.append({"type": "medium_frequency", "weight": op_score, "ops": recent_ops})

        # 因素4: 异常关键词检测 (0-0.2)
        if context.get('has_error_keywords', False):
            score += 0.2
            factors.append({"type": "error_keywords", "weight": 0.2})

        # 因素5: 验证码检测 (0-0.25)
        if context.get('has_captcha', False):
            score += 0.25
            factors.append({"type": "captcha_detected", "weight": 0.25})

        # 因素6: URL跳转异常 (0-0.15)
        if context.get('url_redirected', False):
            score += 0.15
            factors.append({"type": "url_redirect", "weight": 0.15})

        final_score = min(score, 1.0)
        return final_score, factors

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

    def record_result(self, success: bool, risk_score: float = None, context: dict = None):
        """
        记录结果，更新连续成功/失败计数
        """
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
        self.recent_operations = 0
        self.last_reset_time = datetime.utcnow()

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "consecutive_success": self.consecutive_success,
            "consecutive_fail": self.consecutive_fail,
            "current_threshold": self.calculate_threshold(),
            "base_threshold": self.base_threshold,
            "min_threshold": self.min_threshold,
            "risk_history_count": len(self.risk_history)
        }


# 全局单例
risk_score_engine = RiskScoreEngine()