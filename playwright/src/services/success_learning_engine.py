"""
V3.3 Success Learning Engine
远程学习申请记录并动态调整权重

基于 apply 记录学习成功/失败模式，动态调整特征权重
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json


@dataclass
class ApplyRecord:
    """
    Apply record - 申请记录

    Attributes:
        job_id: 职位ID
        company: 公司名称
        title: 职位标题
        page_type: 页面类型 (login/job_list/job_detail/popup/form/captcha)
        result: 结果 (success/fail)
        failure_reason: 失败原因 (login/popup/unknown/captcha/blocked)
        features: 特征字典
        timestamp: 记录时间
    """
    job_id: str
    company: str
    title: str
    page_type: str  # login/job_list/job_detail/popup/form/captcha
    result: str  # success/fail
    failure_reason: str  # login/popup/unknown/captcha/blocked
    features: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearningStats:
    """
    Learning statistics - 学习统计

    Attributes:
        total_applies: 总申请数
        successful_applies: 成功申请数
        failed_applies: 失败申请数
        company_success_rates: 各公司成功率
        page_type_success_rates: 各页面类型成功率
        feature_weights: 特征权重字典
    """
    total_applies: int = 0
    successful_applies: int = 0
    failed_applies: int = 0
    company_success_rates: Dict[str, float] = field(default_factory=dict)
    page_type_success_rates: Dict[str, float] = field(default_factory=dict)
    feature_weights: Dict[str, float] = field(default_factory=lambda: {
        'company_type': 1.0,
        'page_complexity': 1.0,
        'button_layout': 1.0,
        'login_frequency': 1.0,
        'popup_frequency': 1.0,
        'embedding_confidence': 1.0
    })


class SuccessLearningEngine:
    """
    V3.3 Success Learning Engine
    成功学习引擎

    功能:
    - 追踪每一条申请记录（成功/失败）
    - 学习哪些职位/公司/成功模式有效
    - 基于反馈动态调整权重
    - 学习维度: company_type, page_complexity, button_layout, login_frequency, popup_frequency, embedding_confidence

    示例:
        engine = SuccessLearningEngine()
        engine.record_apply(ApplyRecord(
            job_id="job_123",
            company="Example Corp",
            title="Software Engineer",
            page_type="job_detail",
            result="success",
            failure_reason="",
            features={"company_type": "tech", "page_complexity": 0.3}
        ))
        rate = engine.get_success_rate(company="Example Corp")
    """

    # 权重调整常量
    SUCCESS_WEIGHT_MULTIPLIER = 1.1  # 成功时权重乘数
    FAILURE_WEIGHT_MULTIPLIER = 0.9  # 失败时权重乘数
    MAX_WEIGHT = 2.0  # 最大权重
    MIN_WEIGHT = 0.1  # 最小权重

    # 继续申请阈值
    MIN_SUCCESS_RATE_THRESHOLD = 0.1  # 最低成功率阈值
    MAX_FAILURE_STREAK = 5  # 最大连续失败次数

    def __init__(self):
        """初始化成功学习引擎"""
        self.records: List[ApplyRecord] = []
        self.stats = LearningStats()
        self._failure_streak: int = 0  # 连续失败计数

    def record_apply(self, record: ApplyRecord) -> None:
        """
        Record an apply attempt - 记录一次申请尝试

        Args:
            record: ApplyRecord 对象

        工作流程:
            1. 添加 ApplyRecord 到内部列表
            2. 更新成功/失败计数
            3. 调用 update_stats() 更新统计
        """
        try:
            # 验证 record 类型
            if not isinstance(record, ApplyRecord):
                raise TypeError(f"Expected ApplyRecord, got {type(record)}")

            # 添加到记录列表
            self.records.append(record)

            # 更新成功/失败计数
            self.stats.total_applies += 1
            if record.result == "success":
                self.stats.successful_applies += 1
                self._failure_streak = 0  # 重置连续失败计数
            else:
                self.stats.failed_applies += 1
                self._failure_streak += 1

            # 更新统计信息
            self.update_stats()

        except Exception as e:
            raise RuntimeError(f"Failed to record apply: {e}")

    def update_stats(self) -> None:
        """
        Update learning statistics - 更新学习统计

        计算:
            - 各公司的成功率
            - 各页面类型的成功率
            - 基于结果调整特征权重
        """
        if not self.records:
            return

        # 按公司分组计算成功率
        company_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'success': 0, 'total': 0})
        # 按页面类型分组计算成功率
        page_type_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'success': 0, 'total': 0})

        for record in self.records:
            # 公司统计
            company_stats[record.company]['total'] += 1
            if record.result == "success":
                company_stats[record.company]['success'] += 1

            # 页面类型统计
            page_type_stats[record.page_type]['total'] += 1
            if record.result == "success":
                page_type_stats[record.page_type]['success'] += 1

        # 计算成功率
        self.stats.company_success_rates = {
            company: stats['success'] / stats['total']
            if stats['total'] > 0 else 0.0
            for company, stats in company_stats.items()
        }

        self.stats.page_type_success_rates = {
            page_type: stats['success'] / stats['total']
            if stats['total'] > 0 else 0.0
            for page_type, stats in page_type_stats.items()
        }

        # 调整特征权重
        self._adjust_feature_weights()

    def _adjust_feature_weights(self) -> None:
        """
        Adjust feature weights based on outcomes - 基于结果调整特征权重

        调整规则:
            - 成功: weight *= 1.1 (上限 2.0)
            - 失败: weight *= 0.9 (下限 0.1)
        """
        # 获取最近一条记录来调整权重
        if not self.records:
            return

        latest_record = self.records[-1]
        features = latest_record.features

        # 确定是成功还是失败
        is_success = latest_record.result == "success"
        multiplier = self.SUCCESS_WEIGHT_MULTIPLIER if is_success else self.FAILURE_WEIGHT_MULTIPLIER

        # 调整每个特征的权重
        for feature_name in self.stats.feature_weights.keys():
            if feature_name in features:
                current_weight = self.stats.feature_weights[feature_name]
                new_weight = current_weight * multiplier

                # 限制权重范围
                new_weight = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, new_weight))
                self.stats.feature_weights[feature_name] = new_weight

    def get_success_rate(self, company: str = None, page_type: str = None) -> float:
        """
        Get success rate for company or page type - 获取公司或页面类型的成功率

        Args:
            company: 公司名称（可选）
            page_type: 页面类型（可选）

        Returns:
            float: 成功率 (0.0 - 1.0)

        Note:
            - 如果同时提供 company 和 page_type，优先使用 company
            - 如果数据不存在，返回 0.0
        """
        if company is not None:
            return self.stats.company_success_rates.get(company, 0.0)

        if page_type is not None:
            return self.stats.page_type_success_rates.get(page_type, 0.0)

        # 如果都没有提供，返回总体成功率
        if self.stats.total_applies > 0:
            return self.stats.successful_applies / self.stats.total_applies

        return 0.0

    def get_feature_weight(self, feature: str) -> float:
        """
        Get dynamic weight for a feature - 获取特征动态权重

        Args:
            feature: 特征名称

        Returns:
            float: 特征权重值
            - 权重越高 = 使用该特征时越容易成功
            - 默认权重为 1.0

        Supported features:
            - company_type
            - page_complexity
            - button_layout
            - login_frequency
            - popup_frequency
            - embedding_confidence
        """
        return self.stats.feature_weights.get(feature, 1.0)

    def should_continue(self, context: Dict = None) -> bool:
        """
        Decide whether to continue applying based on learning - 基于学习决定是否继续申请

        Args:
            context: 上下文信息字典（可选），可能包含:
                - company: 当前公司
                - page_type: 当前页面类型
                - min_success_rate: 自定义最低成功率

        Returns:
            bool: True 继续申请, False 停止申请

        停止条件:
            1. 当前成功率低于阈值
            2. 连续失败次数超过最大值
            3. 针对特定公司的成功率过低
        """
        context = context or {}

        # 检查连续失败次数
        if self._failure_streak >= self.MAX_FAILURE_STREAK:
            return False

        # 获取最低成功率阈值
        min_rate = context.get('min_success_rate', self.MIN_SUCCESS_RATE_THRESHOLD)

        # 检查总体成功率
        overall_rate = self.get_success_rate()
        if overall_rate < min_rate and self.stats.total_applies >= 5:
            return False

        # 检查特定公司成功率
        if 'company' in context:
            company_rate = self.get_success_rate(company=context['company'])
            if company_rate > 0 and company_rate < min_rate:
                # 如果该公司申请次数>=3且成功率低，停止
                company_apply_count = sum(1 for r in self.records if r.company == context['company'])
                if company_apply_count >= 3:
                    return False

        # 检查特定页面类型成功率
        if 'page_type' in context:
            page_type_rate = self.get_success_rate(page_type=context['page_type'])
            if page_type_rate > 0 and page_type_rate < min_rate:
                # 如果该页面类型申请次数>=3且成功率低，考虑警告但不禁用
                page_type_count = sum(1 for r in self.records if r.page_type == context['page_type'])
                if page_type_count >= 5:
                    return False

        return True

    def export_learning(self) -> Dict:
        """
        Export learning data for persistence - 导出学习数据用于持久化

        Returns:
            Dict: 包含所有学习数据的字典，可序列化为JSON

        导出的数据包括:
            - records: 所有申请记录
            - stats: 学习统计
            - failure_streak: 连续失败次数
        """
        export_data = {
            'records': [
                {
                    'job_id': r.job_id,
                    'company': r.company,
                    'title': r.title,
                    'page_type': r.page_type,
                    'result': r.result,
                    'failure_reason': r.failure_reason,
                    'features': r.features,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in self.records
            ],
            'stats': {
                'total_applies': self.stats.total_applies,
                'successful_applies': self.stats.successful_applies,
                'failed_applies': self.stats.failed_applies,
                'company_success_rates': self.stats.company_success_rates,
                'page_type_success_rates': self.stats.page_type_success_rates,
                'feature_weights': self.stats.feature_weights
            },
            'failure_streak': self._failure_streak,
            'export_timestamp': datetime.now().isoformat()
        }

        return export_data

    def import_learning(self, data: Dict) -> None:
        """
        Import learning data - 导入学习数据

        Args:
            data: 包含学习数据的字典（通常从JSON加载）

        Raises:
            ValueError: 数据格式不正确时抛出

        工作流程:
            1. 验证数据格式
            2. 重建 ApplyRecord 列表
            3. 恢复 LearningStats
            4. 恢复 failure_streak
        """
        try:
            # 验证必需字段
            if 'records' not in data or 'stats' not in data:
                raise ValueError("Invalid data format: missing 'records' or 'stats'")

            # 重建申请记录
            self.records = []
            for record_data in data['records']:
                record = ApplyRecord(
                    job_id=record_data['job_id'],
                    company=record_data['company'],
                    title=record_data['title'],
                    page_type=record_data['page_type'],
                    result=record_data['result'],
                    failure_reason=record_data['failure_reason'],
                    features=record_data['features'],
                    timestamp=datetime.fromisoformat(record_data['timestamp'])
                )
                self.records.append(record)

            # 恢复统计信息
            stats_data = data['stats']
            self.stats = LearningStats(
                total_applies=stats_data.get('total_applies', 0),
                successful_applies=stats_data.get('successful_applies', 0),
                failed_applies=stats_data.get('failed_applies', 0),
                company_success_rates=stats_data.get('company_success_rates', {}),
                page_type_success_rates=stats_data.get('page_type_success_rates', {}),
                feature_weights=stats_data.get('feature_weights', {
                    'company_type': 1.0,
                    'page_complexity': 1.0,
                    'button_layout': 1.0,
                    'login_frequency': 1.0,
                    'popup_frequency': 1.0,
                    'embedding_confidence': 1.0
                })
            )

            # 恢复连续失败计数
            self._failure_streak = data.get('failure_streak', 0)

        except Exception as e:
            raise ValueError(f"Failed to import learning data: {e}")

    def save_to_file(self, file_path: str) -> None:
        """
        Save learning data to JSON file - 保存学习数据到JSON文件

        Args:
            file_path: 文件路径

        Raises:
            IOError: 文件写入失败时抛出
        """
        try:
            export_data = self.export_learning()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save learning data to file: {e}")

    def load_from_file(self, file_path: str) -> None:
        """
        Load learning data from JSON file - 从JSON文件加载学习数据

        Args:
            file_path: 文件路径

        Raises:
            IOError: 文件读取失败时抛出
            ValueError: 数据格式不正确时抛出
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.import_learning(data)
        except Exception as e:
            raise IOError(f"Failed to load learning data from file: {e}")

    def get_recent_records(self, count: int = 10) -> List[ApplyRecord]:
        """
        Get recent apply records - 获取最近的申请记录

        Args:
            count: 返回记录数量，默认10条

        Returns:
            List[ApplyRecord]: 最近的申请记录列表
        """
        return self.records[-count:] if self.records else []

    def get_company_ranking(self) -> List[tuple]:
        """
        Get company success rate ranking - 获取公司成功率排名

        Returns:
            List[tuple]: [(company, success_rate), ...]，按成功率降序排列
        """
        rankings = [
            (company, rate)
            for company, rate in self.stats.company_success_rates.items()
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def get_page_type_ranking(self) -> List[tuple]:
        """
        Get page type success rate ranking - 获取页面类型成功率排名

        Returns:
            List[tuple]: [(page_type, success_rate), ...]，按成功率降序排列
        """
        rankings = [
            (page_type, rate)
            for page_type, rate in self.stats.page_type_success_rates.items()
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def reset(self) -> None:
        """
        Reset all learning data - 重置所有学习数据

        Warning:
            此操作不可逆！
        """
        self.records.clear()
        self.stats = LearningStats()
        self._failure_streak = 0

    def __repr__(self) -> str:
        """String representation of SuccessLearningEngine"""
        return (
            f"SuccessLearningEngine("
            f"records={len(self.records)}, "
            f"total_applies={self.stats.total_applies}, "
            f"success_rate={self.get_success_rate():.2%})"
        )
