"""
V3.3 Job Memory Graph - 任务记忆图谱
用于跟踪职位申请状态和职位关系

Author: AI Assistant
Version: 3.3
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import json


class JobStatus(Enum):
    """职位申请状态枚举"""
    NEW = "new"                      # 新职位
    VIEWED = "viewed"                # 已查看
    INTERESTED = "interested"        # 感兴趣
    APPLIED = "applied"              # 已申请
    SUCCESS = "success"             # 成功(收到回复/面试)
    REJECTED = "rejected"            # 被拒绝
    EXPIRED = "expired"              # 已过期
    NOT_INTERESTED = "not_interested"  # 不感兴趣


@dataclass
class JobNode:
    """
    职位节点 - 表示记忆图谱中的一个职位
    """
    job_id: str
    company: str
    title: str
    url: str
    status: JobStatus = JobStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    neighbors: Set[str] = field(default_factory=set)  # 相关职位ID集合

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "job_id": self.job_id,
            "company": self.company,
            "title": self.title,
            "url": self.url,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "neighbors": list(self.neighbors)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobNode':
        """从字典创建节点"""
        status = JobStatus(data.get("status", "new"))
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            job_id=data["job_id"],
            company=data["company"],
            title=data["title"],
            url=data.get("url", ""),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {}),
            neighbors=set(data.get("neighbors", []))
        )


class JobMemoryGraph:
    """
    V3.3 职位记忆图谱

    用于跟踪职位申请状态和职位关系
    - 追踪已申请职位、感兴趣的职位、失败记录
    - 映射职位位置和状态
    - 建立职位关系网络

    使用 defaultdict 自动创建索引:
    - company_jobs: 公司 -> 职位ID列表
    - tag_jobs: 标签 -> 职位ID集合
    - status_index: 状态 -> 职位ID集合
    """

    def __init__(self):
        """初始化职位记忆图谱"""
        self.jobs: Dict[str, JobNode] = {}  # job_id -> JobNode
        self.company_jobs: Dict[str, List[str]] = defaultdict(list)  # company -> [job_ids]
        self.tag_jobs: Dict[str, Set[str]] = defaultdict(set)  # tag -> {job_ids}
        self.status_index: Dict[JobStatus, Set[str]] = defaultdict(set)  # status -> {job_ids}

    def add_job(self, job_data: Dict) -> str:
        """
        添加职位到记忆图谱

        Args:
            job_data: 职位数据字典，包含以下字段:
                - job_id: 职位ID (必需)
                - company: 公司名称 (必需)
                - title: 职位标题 (必需)
                - url: 职位链接
                - status: 状态，默认为 NEW
                - tags: 标签列表
                - metadata: 其他元数据

        Returns:
            str: 添加的职位ID

        Raises:
            ValueError: 当 job_id, company 或 title 缺失时
        """
        # 验证必需字段
        job_id = job_data.get("job_id")
        company = job_data.get("company")
        title = job_data.get("title")

        if not job_id:
            raise ValueError("job_id 是必需字段")
        if not company:
            raise ValueError("company 是必需字段")
        if not title:
            raise ValueError("title 是必需字段")

        # 检查是否已存在
        if job_id in self.jobs:
            # 更新现有职位
            job_node = self.jobs[job_id]
            job_node.company = company
            job_node.title = title
            job_node.url = job_data.get("url", job_node.url)
            job_node.metadata.update(job_data.get("metadata", {}))
            job_node.updated_at = datetime.now()
            return job_id

        # 解析状态
        status_value = job_data.get("status", JobStatus.NEW.value)
        if isinstance(status_value, str):
            status = JobStatus(status_value)
        else:
            status = status_value

        # 创建新节点
        metadata = job_data.get("metadata", {}).copy()
        # 将 tags 添加到 metadata 中便于存储
        if "tags" in job_data:
            metadata["tags"] = job_data["tags"]

        job_node = JobNode(
            job_id=job_id,
            company=company,
            title=title,
            url=job_data.get("url", ""),
            status=status,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata,
            neighbors=set()
        )

        # 添加到主存储
        self.jobs[job_id] = job_node

        # 索引: 公司
        self.company_jobs[company].append(job_id)

        # 索引: 标签
        tags = job_data.get("tags", [])
        for tag in tags:
            self.tag_jobs[tag].add(job_id)

        # 索引: 状态
        self.status_index[status].add(job_id)

        return job_id

    def update_job_status(self, job_id: str, status: JobStatus) -> bool:
        """
        更新职位状态

        Args:
            job_id: 职位ID
            status: 新状态

        Returns:
            bool: 是否更新成功
        """
        if job_id not in self.jobs:
            return False

        job_node = self.jobs[job_id]
        old_status = job_node.status

        # 从旧状态索引中移除
        if old_status in self.status_index:
            self.status_index[old_status].discard(job_id)

        # 更新状态
        job_node.status = status
        job_node.updated_at = datetime.now()

        # 添加到新状态索引
        self.status_index[status].add(job_id)

        return True

    def get_job(self, job_id: str) -> Optional[JobNode]:
        """
        根据ID获取职位

        Args:
            job_id: 职位ID

        Returns:
            JobNode 或 None
        """
        return self.jobs.get(job_id)

    def get_jobs_by_company(self, company: str) -> List[JobNode]:
        """
        获取公司的所有职位

        Args:
            company: 公司名称

        Returns:
            职位节点列表
        """
        job_ids = self.company_jobs.get(company, [])
        return [self.jobs[job_id] for job_id in job_ids if job_id in self.jobs]

    def get_jobs_by_status(self, status: JobStatus) -> List[JobNode]:
        """
        获取指定状态的所有职位

        Args:
            status: 职位状态

        Returns:
            职位节点列表
        """
        job_ids = self.status_index.get(status, set())
        return [self.jobs[job_id] for job_id in job_ids if job_id in self.jobs]

    def get_applied_jobs(self) -> List[JobNode]:
        """
        获取所有已申请的职位

        Returns:
            已申请职位列表
        """
        return self.get_jobs_by_status(JobStatus.APPLIED)

    def get_interested_jobs(self) -> List[JobNode]:
        """
        获取所有感兴趣的职位

        Returns:
            感兴趣的职位列表
        """
        return self.get_jobs_by_status(JobStatus.INTERESTED)

    def add_relationship(self, job_id1: str, job_id2: str) -> bool:
        """
        在两个职位之间添加关系

        Args:
            job_id1: 职位1 ID
            job_id2: 职位2 ID

        Returns:
            bool: 是否添加成功
        """
        if job_id1 not in self.jobs or job_id2 not in self.jobs:
            return False
        if job_id1 == job_id2:
            return False

        # 互相添加到邻居集合
        self.jobs[job_id1].neighbors.add(job_id2)
        self.jobs[job_id2].neighbors.add(job_id1)

        return True

    def remove_relationship(self, job_id1: str, job_id2: str) -> bool:
        """
        移除两个职位之间的关系

        Args:
            job_id1: 职位1 ID
            job_id2: 职位2 ID

        Returns:
            bool: 是否移除成功
        """
        if job_id1 not in self.jobs or job_id2 not in self.jobs:
            return False

        self.jobs[job_id1].neighbors.discard(job_id2)
        self.jobs[job_id2].discard(job_id1)

        return True

    def get_related_jobs(self, job_id: str) -> List[JobNode]:
        """
        获取与指定职位相关的所有职位

        Args:
            job_id: 职位ID

        Returns:
            相关职位列表
        """
        if job_id not in self.jobs:
            return []

        job_node = self.jobs[job_id]
        related_ids = job_node.neighbors
        return [self.jobs[job_id] for job_id in related_ids if job_id in self.jobs]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆图谱统计信息

        Returns:
            包含各种统计数据的字典:
            - total_jobs: 总职位数
            - by_status: 各状态职位数量
            - by_company: 各公司职位数量
            - success_rate: 成功率 (成功数 / 已处理数)
            - top_companies: 职位最多的公司
            - recent_updated: 最近更新的职位数 (7天内)
        """
        total_jobs = len(self.jobs)

        # 按状态统计
        by_status = {
            status.value: len(self.status_index.get(status, set()))
            for status in JobStatus
        }

        # 按公司统计
        by_company = {
            company: len(job_ids)
            for company, job_ids in self.company_jobs.items()
        }

        # 计算成功率
        success_count = len(self.status_index.get(JobStatus.SUCCESS, set()))
        rejected_count = len(self.status_index.get(JobStatus.REJECTED, set()))
        expired_count = len(self.status_index.get(JobStatus.EXPIRED, set()))

        processed_count = success_count + rejected_count + expired_count
        success_rate = (success_count / processed_count * 100) if processed_count > 0 else 0.0

        # 职位最多的公司
        top_companies = sorted(by_company.items(), key=lambda x: x[1], reverse=True)[:10]

        # 最近7天更新的职位数
        seven_days_ago = datetime.now().timestamp() - 7 * 24 * 60 * 60
        recent_updated = sum(
            1 for job in self.jobs.values()
            if job.updated_at.timestamp() > seven_days_ago
        )

        return {
            "total_jobs": total_jobs,
            "by_status": by_status,
            "by_company": by_company,
            "success_rate": round(success_rate, 2),
            "top_companies": top_companies,
            "recent_updated": recent_updated,
            "total_companies": len(by_company),
            "total_relationships": sum(len(job.neighbors) for job in self.jobs.values()) // 2
        }

    def export_data(self) -> Dict:
        """
        导出记忆图谱数据为字典格式

        Returns:
            包含所有职位数据的字典，可用于 JSON 序列化
        """
        return {
            "version": "3.3",
            "exported_at": datetime.now().isoformat(),
            "jobs": {
                job_id: job_node.to_dict()
                for job_id, job_node in self.jobs.items()
            },
            "company_jobs": {
                company: job_ids
                for company, job_ids in self.company_jobs.items()
            },
            "tag_jobs": {
                tag: list(job_ids)
                for tag, job_ids in self.tag_jobs.items()
            },
            "status_index": {
                status.value: list(job_ids)
                for status, job_ids in self.status_index.items()
            }
        }

    def import_data(self, data: Dict) -> bool:
        """
        从字典数据导入记忆图谱

        Args:
            data: 导出的数据字典

        Returns:
            bool: 是否导入成功
        """
        try:
            # 清空现有数据
            self.jobs.clear()
            self.company_jobs.clear()
            self.tag_jobs.clear()
            self.status_index.clear()

            # 恢复职位数据
            jobs_data = data.get("jobs", {})
            for job_id, job_dict in jobs_data.items():
                job_node = JobNode.from_dict(job_dict)
                self.jobs[job_id] = job_node

            # 恢复公司索引
            company_jobs_data = data.get("company_jobs", {})
            for company, job_ids in company_jobs_data.items():
                self.company_jobs[company] = job_ids

            # 恢复标签索引
            tag_jobs_data = data.get("tag_jobs", {})
            for tag, job_ids in tag_jobs_data.items():
                self.tag_jobs[tag] = set(job_ids)

            # 恢复状态索引
            status_index_data = data.get("status_index", {})
            for status_str, job_ids in status_index_data.items():
                status = JobStatus(status_str)
                self.status_index[status] = set(job_ids)

            return True

        except Exception as e:
            print(f"导入数据失败: {e}")
            return False

    def find_similar_jobs(self, job_id: str, limit: int = 5) -> List[JobNode]:
        """
        根据公司和标题相似度查找相似职位

        Args:
            job_id: 职位ID
            limit: 返回数量限制

        Returns:
            相似职位列表，按相似度排序
        """
        if job_id not in self.jobs:
            return []

        target_job = self.jobs[job_id]
        target_company = target_job.company.lower()
        target_title = target_job.title.lower()

        # 计算相似度分数
        similar_jobs = []
        for other_id, other_job in self.jobs.items():
            if other_id == job_id:
                continue

            score = 0

            # 公司相同得高分
            if other_job.company.lower() == target_company:
                score += 10

            # 标题相似度 (简单基于关键词重叠)
            target_words = set(target_title.split())
            other_words = set(other_job.title.lower().split())

            # 计算标题词汇重叠
            if target_words and other_words:
                overlap = len(target_words & other_words)
                total = len(target_words | other_words)
                if total > 0:
                    title_similarity = overlap / total
                    score += title_similarity * 5

            # 已有关系的职位优先
            if job_id in other_job.neighbors:
                score += 3

            if score > 0:
                similar_jobs.append((other_id, score))

        # 按分数排序
        similar_jobs.sort(key=lambda x: x[1], reverse=True)

        # 返回前 limit 个
        return [self.jobs[job_id] for job_id, _ in similar_jobs[:limit]]

    def get_jobs_by_tag(self, tag: str) -> List[JobNode]:
        """
        根据标签获取职位

        Args:
            tag: 标签名称

        Returns:
            职位节点列表
        """
        job_ids = self.tag_jobs.get(tag, set())
        return [self.jobs[job_id] for job_id in job_ids if job_id in self.jobs]

    def search_jobs(self, keyword: str) -> List[JobNode]:
        """
        在职位标题和公司名称中搜索关键词

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的职位列表
        """
        keyword_lower = keyword.lower()
        results = []

        for job in self.jobs.values():
            if (keyword_lower in job.company.lower() or
                keyword_lower in job.title.lower()):
                results.append(job)

        return results

    def delete_job(self, job_id: str) -> bool:
        """
        从记忆图谱中删除职位

        Args:
            job_id: 职位ID

        Returns:
            bool: 是否删除成功
        """
        if job_id not in self.jobs:
            return False

        job_node = self.jobs[job_id]

        # 从公司索引中移除
        if job_node.company in self.company_jobs:
            self.company_jobs[job_node.company] = [
                jid for jid in self.company_jobs[job_node.company]
                if jid != job_id
            ]

        # 从标签索引中移除
        tags = job_node.metadata.get("tags", [])
        for tag in tags:
            if tag in self.tag_jobs:
                self.tag_jobs[tag].discard(job_id)

        # 从状态索引中移除
        if job_node.status in self.status_index:
            self.status_index[job_node.status].discard(job_id)

        # 从邻居节点的邻居集合中移除
        for neighbor_id in job_node.neighbors:
            if neighbor_id in self.jobs:
                self.jobs[neighbor_id].neighbors.discard(job_id)

        # 从主存储中删除
        del self.jobs[job_id]

        return True

    def clear_all(self):
        """清空所有记忆图谱数据"""
        self.jobs.clear()
        self.company_jobs.clear()
        self.tag_jobs.clear()
        self.status_index.clear()

    def __len__(self) -> int:
        """返回记忆图谱中的职位数量"""
        return len(self.jobs)

    def __repr__(self) -> str:
        """返回记忆图谱的字符串表示"""
        stats = self.get_statistics()
        return (
            f"JobMemoryGraph("
            f"total_jobs={stats['total_jobs']}, "
            f"total_companies={stats['total_companies']}, "
            f"success_rate={stats['success_rate']}%)"
        )


# 示例用法和测试
if __name__ == "__main__":
    # 创建记忆图谱实例
    graph = JobMemoryGraph()

    # 添加职位数据
    job1 = {
        "job_id": "boss_zp123456",
        "company": "腾讯科技",
        "title": "高级Python工程师",
        "url": "https://www.zhipin.com/job/xxx",
        "salary": "25k-40k",
        "city": "深圳",
        "tags": ["后端", "Python", "Golang"],
        "source": "boss"
    }

    job2 = {
        "job_id": "boss_zp234567",
        "company": "腾讯科技",
        "title": "资深Python开发工程师",
        "url": "https://www.zhipin.com/job/yyy",
        "tags": ["后端", "Python"],
        "status": "interested"
    }

    job3 = {
        "job_id": "boss_zp345678",
        "company": "阿里巴巴",
        "title": "Go开发工程师",
        "url": "https://www.zhipin.com/job/zzz",
        "tags": ["后端", "Golang"],
        "status": "applied"
    }

    # 添加职位
    graph.add_job(job1)
    graph.add_job(job2)
    graph.add_job(job3)

    # 添加关系
    graph.add_relationship("boss_zp123456", "boss_zp234567")

    # 更新状态
    graph.update_job_status("boss_zp123456", JobStatus.APPLIED)

    # 查询
    print("=== 记忆图谱信息 ===")
    print(f"职位总数: {len(graph)}")
    print(f"腾讯科技职位: {[j.title for j in graph.get_jobs_by_company('腾讯科技')]}")
    print(f"已申请职位: {[j.title for j in graph.get_applied_jobs()]}")
    print(f"相关职位: {[j.title for j in graph.get_related_jobs('boss_zp123456')]}")
    print(f"相似职位: {[j.title for j in graph.find_similar_jobs('boss_zp123456')]}")

    # 统计
    print("\n=== 统计信息 ===")
    stats = graph.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 导出/导入测试
    print("\n=== 导出导入测试 ===")
    exported = graph.export_data()
    print(f"导出数据包含 {len(exported['jobs'])} 个职位")

    new_graph = JobMemoryGraph()
    new_graph.import_data(exported)
    print(f"导入后职位数: {len(new_graph)}")
