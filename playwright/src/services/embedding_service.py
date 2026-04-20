"""
V3.3 Embedding Service
使用 Doubao-embedding 进行文本向量化

功能说明:
- 使用豆包embedding模型进行文本向量化
- 提供job matching的相似度评分(apply/login/bookmark操作)
- 统一平台job descriptions
- 作为Vision的fallback方案
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import httpx
import base64
import asyncio
import math


@dataclass
class EmbeddingResult:
    """Embedding结果数据类"""
    embedding: List[float]
    index: int = 0


class EmbeddingService:
    """
    V3.3 Embedding Service
    使用Doubao-embedding进行文本向量化

    Attributes:
        api_key: 豆包API密钥
        base_url: API基础URL
        model:  embedding模型名称
    """

    # V3.3 Doubao API 配置
    API_KEY = "fddc1778-d04c-403e-8327-ab68ec1ec9dd"
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    EMBEDDING_MODEL = "doubao-embedding-vision-251215"

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化Embedding服务

        Args:
            api_key: 豆包API密钥
            base_url: API基础URL
        """
        self.api_key = api_key or self.API_KEY
        self.base_url = base_url or self.BASE_URL
        self.model = self.EMBEDDING_MODEL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建httpx异步客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client

    async def close(self):
        """关闭HTTP客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度

        Args:
            vec1: 第一个向量
            vec2: 第二个向量

        Returns:
            余弦相似度值，范围[-1, 1]
        """
        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def encode(self, texts: List[str]) -> List[List[float]]:
        """
        将文本列表编码为embedding向量

        Args:
            texts: 要编码的文本列表

        Returns:
            embedding向量列表，每个文本对应一个向量
        """
        if not texts:
            return []

        print(f"[Embedding API] 调用 encode, 文本数量: {len(texts)}")

        try:
            client = await self._get_client()
            embeddings = []

            # multimodal API 每次调用只返回一个embedding，需要逐个调用
            for i, text in enumerate(texts):
                print(f"[Embedding API] 编码第 {i+1}/{len(texts)} 个文本: {text[:50]}...")
                response = await client.post(
                    f"{self.base_url}/embeddings/multimodal",
                    json={
                        "model": self.model,
                        "input": [{"type": "text", "text": text}]
                    }
                )
                response.raise_for_status()
                result = response.json()

                if "data" in result and isinstance(result["data"], dict) and "embedding" in result["data"]:
                    embeddings.append(result["data"]["embedding"])
                    print(f"[Embedding API] 第 {i+1} 个文本 embedding 长度: {len(result['data']['embedding'])}")
                else:
                    embeddings.append([])
                    print(f"[Embedding API] 第 {i+1} 个文本 embedding 为空")

            return embeddings

        except httpx.HTTPStatusError as e:
            print(f"Embedding API HTTP错误: {e.response.status_code} - {e.response.text}")
            return [[] for _ in texts]
            return [[] for _ in texts]
        except httpx.RequestError as e:
            print(f"Embedding API请求错误: {str(e)}")
            return [[] for _ in texts]
        except Exception as e:
            print(f"Embedding API未知错误: {str(e)}")
            return [[] for _ in texts]

    async def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本之间的余弦相似度

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            相似度分数，范围[0, 1]。0表示完全不相似，1表示完全相似
        """
        if not text1 or not text2:
            return 0.0

        try:
            embeddings = await self.encode([text1, text2])

            if len(embeddings) < 2:
                return 0.0

            embedding1 = embeddings[0]
            embedding2 = embeddings[1]

            if not embedding1 or not embedding2:
                return 0.0

            # 余弦相似度范围转换到[0, 1]
            similarity = self._cosine_similarity(embedding1, embedding2)
            return (similarity + 1) / 2

        except Exception as e:
            print(f"计算相似度错误: {str(e)}")
            return 0.0

    async def find_best_match(self, query: str, candidates: List[Dict]) -> Optional[Dict]:
        """
        从候选列表中找到与查询最匹配的对象

        Args:
            query: 查询文本
            candidates: 候选对象列表，每个对象应包含'text'字段或可转换为文本的字段

        Returns:
            最匹配的候选对象，如果无有效候选则返回None
        """
        if not query or not candidates:
            return None

        try:
            # 提取候选文本
            candidate_texts = []
            for candidate in candidates:
                if isinstance(candidate, dict):
                    # 优先使用text字段，其次使用description，最后使用name
                    text = candidate.get("text") or candidate.get("description") or candidate.get("name", "")
                elif isinstance(candidate, str):
                    text = candidate
                else:
                    text = str(candidate)
                candidate_texts.append(text)

            # 批量编码查询和候选文本
            all_texts = [query] + candidate_texts
            all_embeddings = await self.batch_encode(all_texts, batch_size=32)

            if not all_embeddings or len(all_embeddings) < len(all_texts):
                return None

            query_embedding = all_embeddings[0]
            candidate_embeddings = all_embeddings[1:]

            if not query_embedding:
                return None

            # 计算每个候选的相似度
            best_match = None
            best_similarity = -1.0

            for i, (candidate, embedding) in enumerate(zip(candidates, candidate_embeddings)):
                if not embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, embedding)
                # 转换为[0, 1]范围
                similarity = (similarity + 1) / 2

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate
                    # 将相似度添加到返回对象中
                    if isinstance(best_match, dict):
                        best_match["_similarity_score"] = similarity

            return best_match

        except Exception as e:
            print(f"查找最佳匹配错误: {str(e)}")
            return None

    async def batch_encode(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """
        批量编码文本，支持分批处理以避免API限制

        Args:
            texts: 要编码的文本列表
            batch_size: 每批处理的文本数量，默认为16

        Returns:
            所有文本的embedding向量列表
        """
        if not texts:
            return []

        all_embeddings = []

        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.encode(batch)
            all_embeddings.extend(embeddings)

            # 避免请求过快，稍作延迟
            if i + batch_size < len(texts):
                await asyncio.sleep(0.05)

        return all_embeddings

    async def encode_job_description(self, job: Dict) -> Optional[List[float]]:
        """
        编码job描述用于匹配

        Args:
            job: job信息字典，应包含title、description、company等字段

        Returns:
            job描述的embedding向量，失败返回None
        """
        if not job:
            return None

        try:
            # 组合job相关信息形成统一描述
            parts = []

            if job.get("title"):
                parts.append(f"职位: {job['title']}")
            if job.get("company"):
                parts.append(f"公司: {job['company']}")
            if job.get("description"):
                parts.append(f"描述: {job['description']}")
            if job.get("requirements"):
                parts.append(f"要求: {job['requirements']}")
            if job.get("location"):
                parts.append(f"地点: {job['location']}")
            if job.get("salary"):
                parts.append(f"薪资: {job['salary']}")

            combined_text = " | ".join(parts)

            if not combined_text:
                return None

            embeddings = await self.encode([combined_text])
            return embeddings[0] if embeddings else None

        except Exception as e:
            print(f"编码job描述错误: {str(e)}")
            return None

    async def compute_job_similarity(self, job1: Dict, job2: Dict) -> float:
        """
        计算两个job之间的相似度

        Args:
            job1: 第一个job信息
            job2: 第二个job信息

        Returns:
            相似度分数，范围[0, 1]
        """
        embedding1 = await self.encode_job_description(job1)
        embedding2 = await self.encode_job_description(job2)

        if not embedding1 or not embedding2:
            return 0.0

        similarity = self._cosine_similarity(embedding1, embedding2)
        return (similarity + 1) / 2

    async def rank_jobs_by_relevance(
        self,
        query: str,
        jobs: List[Dict],
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """
        根据与查询的相关性对job列表进行排序

        Args:
            query: 查询文本
            jobs: job列表
            top_k: 返回前k个结果，None表示返回所有

        Returns:
            按相关性排序的job列表，每个job包含_similarity_score字段
        """
        if not query or not jobs:
            return []

        try:
            # 批量编码所有job
            job_texts = []
            for job in jobs:
                parts = []
                if job.get("title"):
                    parts.append(f"职位: {job['title']}")
                if job.get("company"):
                    parts.append(f"公司: {job['company']}")
                if job.get("description"):
                    parts.append(f"描述: {job['description']}")
                if job.get("requirements"):
                    parts.append(f"要求: {job['requirements']}")
                job_texts.append(" | ".join(parts))

            # 编码查询和所有job
            all_texts = [query] + job_texts
            all_embeddings = await self.batch_encode(all_texts, batch_size=32)

            if not all_embeddings:
                return jobs

            query_embedding = all_embeddings[0]
            job_embeddings = all_embeddings[1:]

            # 计算每个job的相似度
            scored_jobs = []
            for i, (job, embedding) in enumerate(zip(jobs, job_embeddings)):
                if not embedding:
                    similarity = 0.0
                else:
                    similarity = self._cosine_similarity(query_embedding, embedding)
                    similarity = (similarity + 1) / 2

                job_copy = job.copy()
                job_copy["_similarity_score"] = similarity
                scored_jobs.append((similarity, job_copy))

            # 按相似度降序排序
            scored_jobs.sort(key=lambda x: x[0], reverse=True)

            # 提取排序后的job
            ranked_jobs = [job for _, job in scored_jobs]

            if top_k is not None:
                ranked_jobs = ranked_jobs[:top_k]

            return ranked_jobs

        except Exception as e:
            print(f"排序jobs错误: {str(e)}")
            return jobs

    async def search_with_relocation(
        self,
        original_title: str,
        original_company: str,
        search_results: List[Dict],
        similarity_threshold: float = 0.8
    ) -> Optional[Dict]:
        """
        V3.4 搜索重定位功能
        当原始职位URL失效时，通过Embedding匹配找到最相似的替代职位

        Args:
            original_title: 原职位名称
            original_company: 原公司名称
            search_results: 搜索结果列表
            similarity_threshold: 相似度阈值，默认0.8

        Returns:
            最匹配的职位（如果相似度>=阈值），否则返回None
        """
        if not search_results:
            return None

        try:
            # 构建原始职位的查询文本
            original_query = f"{original_title} {original_company}"

            # 构建候选职位的文本
            candidates = []
            for job in search_results:
                title = job.get('title', '')
                company = job.get('company', '')
                candidates.append(f"{title} {company}")

            if not candidates:
                return None

            # 批量编码
            all_texts = [original_query] + candidates
            all_embeddings = await self.batch_encode(all_texts, batch_size=32)

            if not all_embeddings:
                return None

            query_embedding = all_embeddings[0]
            candidate_embeddings = all_embeddings[1:]

            # 计算相似度
            best_match = None
            best_similarity = 0.0

            for i, (job, embedding) in enumerate(zip(search_results, candidate_embeddings)):
                if not embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, embedding)
                similarity = (similarity + 1) / 2

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = job.copy()
                    best_match['_relocation_similarity'] = similarity
                    best_match['_relocation_source'] = f"{original_title}@{original_company}"

            # 只有超过阈值才返回
            if best_similarity >= similarity_threshold:
                print(f"[Embedding] 重定位成功: {original_title} -> {best_match.get('title')}, 相似度: {best_similarity:.2f}")
                return best_match
            else:
                print(f"[Embedding] 重定位失败: {original_title}, 最高相似度: {best_similarity:.2f} < 阈值: {similarity_threshold}")
                return None

        except Exception as e:
            print(f"[Embedding] 重定位错误: {str(e)}")
            return None


# 导出主要类
__all__ = ["EmbeddingService", "EmbeddingResult", "search_with_relocation"]
