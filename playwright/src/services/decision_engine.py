"""
V3.3 Decision Engine
使用 Embedding 相似度进行决策的决策引擎

功能说明:
- 使用Embedding相似度选择最佳apply按钮
- 决策层进行按钮匹配(apply/login/bookmark)
- 统一平台匹配
- 作为Vision的Fallback方案
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import asyncio
import math


@dataclass
class DecisionResult:
    """
    决策结果数据类

    Attributes:
        selected_element: 选中的元素，None表示未找到匹配
        confidence: 置信度分数，范围[0, 1]
        alternatives: 备选元素列表，按相似度降序排列
        reasoning: 决策推理说明
    """
    selected_element: Optional[Dict]
    confidence: float
    alternatives: List[Dict] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class PageClassification:
    """
    页面分类结果

    Attributes:
        page_type: 页面类型 (login/job_list/job_detail/popup/captcha/unknown)
        confidence: 分类置信度，范围[0, 1]
        reasoning: 分类依据说明
    """
    page_type: str
    confidence: float
    reasoning: str = ""


class DecisionEngine:
    """
    V3.3 Decision Engine
    使用Embedding相似度进行智能决策

    Attributes:
        embedding_service: 嵌入服务实例，用于文本向量化和相似度计算
    """

    # 页面分类关键词映射
    PAGE_TYPE_KEYWORDS = {
        "login": ["登录", "login", "sign in", "用户名", "密码", "手机号登录", "验证码登录"],
        "job_list": ["职位", "工作", "jobs", "职位列表", "岗位", "招聘", "职位推荐", "职位搜索"],
        "job_detail": ["职位详情", "职位描述", "job detail", "职位要求", "岗位职责", "任职资格", "申请职位", "投递简历"],
        "popup": ["弹窗", "popup", "提示", "确认", "取消", "关闭", "知道了", "温馨提示"],
        "captcha": ["验证码", " captcha", "拼图", "滑动验证", "安全验证", "人机验证", "点击验证"],
    }

    # Apply按钮目标短语
    APPLY_TARGETS = [
        "投递职位", "立即投递", "申请职位", "投递简历", "立即申请",
        "我要投递", "应聘", "报名", "立即应聘", "投递", "申请",
        "send application", "apply now", "submit", "我要申请",
        "马上申请", "立即申请", "开始申请"
    ]

    # 投递按钮必须包含的正面关键词 - 必须包含这些词之一才可能是投递按钮
    APPLY_REQUIRED_KEYWORDS = [
        "投递", "申请", "应聘", "报名",
        "apply", "submit",
    ]

    # 负面关键词 - 包含这些词的按钮一定不是投递按钮
    APPLY_EXCLUDE_KEYWORDS = [
        "返回", "返回首页", "返回主页", "上一步", "下一步", "取消", "关闭",
        "我要招人", "招聘", "hr", "boss", "直聘", "聊聊", "立即沟通",
        "联系", "电话", "邮箱", "邮件", "message", "chat",
        "查看详情", "查看更多", "展开", "收起", "更多",
        "登录", "注册", "找回密码", "忘记密码",
        "安全", "验证", "协议", "条款", "隐私",
        "收藏", "关注", "分享", "举报", "举报",
        # 额外的常见非投递按钮
        "确定", "确认", "是的", "我同意",
        "刷新", "刷新页面", "重新加载",
        "下载", "导出", "打印",
        "上传", "附件", "简历",
        "搜索", "查找",
        "菜单", "导航", "首页",
    ]
    LOGIN_TARGETS = ["登录", "login", "sign in", "登入", "立即登录", "账号登录"]
    BOOKMARK_TARGETS = ["收藏", "收藏职位", "关注", "加收藏", "mark", "bookmark", "收藏该职位"]

    def __init__(self, embedding_service=None):
        """
        初始化决策引擎

        Args:
            embedding_service: 嵌入服务实例，如果为None则使用内置方法
        """
        self.embedding_service = embedding_service
        self._http_client = None

    async def _get_http_client(self):
        """获取HTTP客户端"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={"Content-Type": "application/json"}
            )
        return self._http_client

    async def close(self):
        """关闭HTTP客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

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

    async def _embed_text(self, text: str) -> Optional[List[float]]:
        """
        使用嵌入服务将文本转换为向量

        Args:
            text: 要嵌入的文本

        Returns:
            文本的嵌入向量，失败返回None
        """
        if not text:
            return None

        # 如果有嵌入服务，使用它
        if self.embedding_service:
            try:
                embeddings = await self.embedding_service.encode([text])
                return embeddings[0] if embeddings else None
            except Exception as e:
                print(f"Embedding服务错误: {str(e)}")
                return None

        # 否则使用内置API调用
        try:
            import os
            api_key = os.environ.get("DOUBAO_API_KEY", "fddc1778-d04c-403e-8327-ab68ec1ec9dd")
            base_url = os.environ.get("DOUBAO_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")

            client = await self._get_http_client()
            response = await client.post(
                f"{base_url}/embeddings/multimodal",
                json={
                    "model": "doubao-embedding-vision-251215",
                    "input": [{"type": "text", "text": text}]
                },
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            result = response.json()

            if "data" in result and isinstance(result["data"], dict) and "embedding" in result["data"]:
                return result["data"]["embedding"]

            return None

        except Exception as e:
            print(f"内置嵌入API错误: {str(e)}")
            return None

    async def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量

        Args:
            texts: 要嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        if not texts:
            return []

        # 如果有嵌入服务，使用它
        if self.embedding_service:
            try:
                return await self.embedding_service.batch_encode(texts, batch_size=32)
            except Exception as e:
                print(f"Embedding服务批量编码错误: {str(e)}")
                return [[] for _ in texts]

        # 否则使用内置API调用
        try:
            import os
            api_key = os.environ.get("DOUBAO_API_KEY", "fddc1778-d04c-403e-8327-ab68ec1ec9dd")
            base_url = os.environ.get("DOUBAO_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")

            client = await self._get_http_client()
            embeddings = []

            # multimodal API 每次调用只返回一个embedding，需要逐个调用
            for text in texts:
                response = await client.post(
                    f"{base_url}/embeddings/multimodal",
                    json={
                        "model": "doubao-embedding-vision-251215",
                        "input": [{"type": "text", "text": text}]
                    },
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                response.raise_for_status()
                result = response.json()

                if "data" in result and isinstance(result["data"], dict) and "embedding" in result["data"]:
                    embeddings.append(result["data"]["embedding"])
                else:
                    embeddings.append([])

            return embeddings

        except Exception as e:
            print(f"内置嵌入API批量编码错误: {str(e)}")
            return [[] for _ in texts]

    async def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本之间的相似度

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            相似度分数，范围[0, 1]
        """
        if not text1 or not text2:
            return 0.0

        embeddings = await self._embed_texts([text1, text2])
        if len(embeddings) < 2 or not embeddings[0] or not embeddings[1]:
            return 0.0

        similarity = self._cosine_similarity(embeddings[0], embeddings[1])
        # 转换到[0, 1]范围
        return (similarity + 1) / 2

    def _normalize_text(self, text: str) -> str:
        """
        规范化文本，去除多余空白字符

        Args:
            text: 原始文本

        Returns:
            规范化后的文本
        """
        if not text:
            return ""
        # 去除多余空白，保留单个空格
        return " ".join(text.split())

    def _extract_element_text(self, element: Dict) -> str:
        """
        从元素中提取文本

        Args:
            element: 元素字典或 UIElement 对象

        Returns:
            元素的文本内容
        """
        if not element:
            return ""

        # 如果是 UIElement 对象，直接访问 text 属性
        if hasattr(element, 'text'):
            return self._normalize_text(element.text)

        # 如果是字典，尝试多种文本字段
        if isinstance(element, dict):
            text = element.get("text") or element.get("inner_text") or element.get("value") or element.get("name") or ""
            return self._normalize_text(text)

        # 其他类型，尝试转字符串
        return self._normalize_text(str(element))

    async def score_element(self, element_text: str, target: str) -> float:
        """
        评分单个元素与目标短语的相关性

        Args:
            element_text: 元素的文本
            target: 目标短语

        Returns:
            相似度分数，范围[0, 1]
        """
        element_text = self._normalize_text(element_text)
        target = self._normalize_text(target)

        if not element_text or not target:
            return 0.0

        return await self._calculate_similarity(element_text, target)

    async def pick_apply_button(self, elements: List[Dict]) -> DecisionResult:
        """
        从元素列表中选择最佳的投递按钮

        使用Embedding相似度算法，对每个候选按钮与目标短语
        "投递职位"、"立即投递"等进行相似度计算，返回最佳匹配

        Args:
            elements: 候选元素列表，每个元素应包含text或inner_text字段

        Returns:
            DecisionResult，包含选中元素、置信度、备选列表和推理说明
        """
        if not elements:
            return DecisionResult(
                selected_element=None,
                confidence=0.0,
                alternatives=[],
                reasoning="元素列表为空，无法选择投递按钮"
            )

        # 过滤有效元素（需要有文本，且不包含负面关键词，必须包含正面关键词）
        valid_elements = []
        debug_buttons = []  # 调试用
        for elem in elements:
            # 获取元素的所有属性用于调试
            if hasattr(elem, 'text'):
                elem_text = elem.text
                elem_type = getattr(elem, 'element_type', 'unknown')
            elif isinstance(elem, dict):
                elem_text = elem.get('text') or elem.get('inner_text') or elem.get('value') or elem.get('name') or ''
                elem_type = elem.get('type', 'unknown')
            else:
                elem_text = str(elem)
                elem_type = 'unknown'

            text = elem_text  # 使用提取的文本
            if not text:
                debug_buttons.append(f"[EMPTY:{elem_type}]")
                continue

            text_lower = text.lower()
            debug_buttons.append(f"['{text}':{elem_type}]")  # 调试用：显示文本和类型

            # 第一步：必须包含正面关键词之一
            has_required_keyword = False
            matched_required = None
            for required_keyword in self.APPLY_REQUIRED_KEYWORDS:
                if required_keyword.lower() in text_lower:
                    has_required_keyword = True
                    matched_required = required_keyword
                    break
            if not has_required_keyword:
                continue  # 不包含任何正面关键词，跳过

            # 第二步：不能包含负面关键词
            excluded = False
            matched_exclude = None
            for exclude_keyword in self.APPLY_EXCLUDE_KEYWORDS:
                if exclude_keyword.lower() in text_lower:
                    excluded = True
                    matched_exclude = exclude_keyword
                    break
            if excluded:
                continue

            # 确保 elem 是 dict 类型
            if isinstance(elem, dict):
                elem_copy = elem.copy()
            elif hasattr(elem, 'to_dict'):
                elem_copy = elem.to_dict()
            elif hasattr(elem, 'text'):
                # UIElement 对象，转换为 dict
                elem_copy = {
                    'text': elem.text,
                    'type': getattr(elem, 'element_type', 'button'),
                    'x': elem.bounding_box.get('x', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                    'y': elem.bounding_box.get('y', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                    'width': elem.bounding_box.get('width', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                    'height': elem.bounding_box.get('height', 0) if hasattr(elem, 'bounding_box') and elem.bounding_box else 0,
                }
            else:
                elem_copy = {'text': str(elem)}
            elem_copy["_extracted_text"] = text
            valid_elements.append(elem_copy)

        # 调试日志：打印所有检测到的按钮和过滤结果
        print(f"[Decision Engine] 检测到 {len(debug_buttons)} 个按钮: {debug_buttons}")
        print(f"[Decision Engine] 过滤后 {len(valid_elements)} 个有效按钮")
        print(f"[Decision Engine] 正面关键词: {self.APPLY_REQUIRED_KEYWORDS}")
        print(f"[Decision Engine] 负面关键词: {self.APPLY_EXCLUDE_KEYWORDS}")

        if not valid_elements:
            # 提供更多调试信息
            debug_info = []
            for elem in elements[:5]:  # 只取前5个
                text = self._extract_element_text(elem)
                debug_info.append(f"'{text[:30] if text else 'None'}'")
            reasoning = f"没有找到符合条件的投递按钮（需包含: {self.APPLY_REQUIRED_KEYWORDS}，且不含排除词）。候选元素: {debug_info}"
            return DecisionResult(
                selected_element=None,
                confidence=0.0,
                alternatives=[],
                reasoning=reasoning
            )

        # 对每个有效元素计算与所有目标短语的最高相似度
        element_scores = []
        for elem in valid_elements:
            element_text = elem["_extracted_text"]

            # 计算与所有Apply目标短语的相似度，取最大值
            best_score = 0.0
            best_target = ""

            for target in self.APPLY_TARGETS:
                score = await self._calculate_similarity(element_text, target)
                if score > best_score:
                    best_score = score
                    best_target = target

            element_scores.append({
                "element": elem,
                "score": best_score,
                "matched_target": best_target,
                "text": element_text
            })

        # 按分数降序排序
        element_scores.sort(key=lambda x: x["score"], reverse=True)

        best = element_scores[0]

        # 最小置信度阈值 - 低于此值认为未找到有效按钮
        # 由于已经过正面关键词过滤，阈值可以适当提高
        MIN_CONFIDENCE = 0.35

        if best["score"] < MIN_CONFIDENCE:
            # 记录调试信息
            top_candidates = [f"{e['text'][:20]}:{e['score']:.3f}" for e in element_scores[:3]]
            reasoning = f"最高相似度 {best['score']:.4f} 低于阈值 {MIN_CONFIDENCE}，未找到有效投递按钮。Top候选: {top_candidates}"
            return DecisionResult(
                selected_element=None,
                confidence=best["score"],
                alternatives=[],
                reasoning=reasoning
            )

        alternatives = [item["element"] for item in element_scores[1:10]]  # 保留前9个作为备选

        reasoning = f"选中元素文本: '{best['text']}'，与目标'{best['matched_target']}'的相似度为 {best['score']:.4f}"

        # 添加备选元素的推理
        if len(element_scores) > 1:
            reasoning += f"，备选数量: {len(element_scores) - 1}"

        return DecisionResult(
            selected_element=best["element"],
            confidence=best["score"],
            alternatives=alternatives,
            reasoning=reasoning
        )

    async def pick_login_action(self, elements: List[Dict]) -> DecisionResult:
        """
        从元素列表中选择最佳的登录按钮

        使用Embedding相似度算法，对每个候选按钮与目标短语
        "登录"、"login"等进行相似度计算，返回最佳匹配

        Args:
            elements: 候选元素列表，每个元素应包含text或inner_text字段

        Returns:
            DecisionResult，包含选中元素、置信度、备选列表和推理说明
        """
        if not elements:
            return DecisionResult(
                selected_element=None,
                confidence=0.0,
                alternatives=[],
                reasoning="元素列表为空，无法选择登录按钮"
            )

        # 过滤有效元素
        valid_elements = []
        for elem in elements:
            text = self._extract_element_text(elem)
            if text:
                elem_copy = elem.copy()
                elem_copy["_extracted_text"] = text
                valid_elements.append(elem_copy)

        if not valid_elements:
            return DecisionResult(
                selected_element=None,
                confidence=0.0,
                alternatives=[],
                reasoning="没有找到包含有效文本的元素"
            )

        # 对每个有效元素计算与所有Login目标短语的最高相似度
        element_scores = []
        for elem in valid_elements:
            element_text = elem["_extracted_text"]

            # 计算与所有Login目标短语的相似度，取最大值
            best_score = 0.0
            best_target = ""

            for target in self.LOGIN_TARGETS:
                score = await self._calculate_similarity(element_text, target)
                if score > best_score:
                    best_score = score
                    best_target = target

            element_scores.append({
                "element": elem,
                "score": best_score,
                "matched_target": best_target,
                "text": element_text
            })

        # 按分数降序排序
        element_scores.sort(key=lambda x: x["score"], reverse=True)

        best = element_scores[0]
        alternatives = [item["element"] for item in element_scores[1:10]]

        reasoning = f"选中元素文本: '{best['text']}'，与目标'{best['matched_target']}'的相似度为 {best['score']:.4f}"

        if len(element_scores) > 1:
            reasoning += f"，备选数量: {len(element_scores) - 1}"

        return DecisionResult(
            selected_element=best["element"],
            confidence=best["score"],
            alternatives=alternatives,
            reasoning=reasoning
        )

    async def pick_bookmark_action(self, elements: List[Dict]) -> DecisionResult:
        """
        从元素列表中选择最佳的收藏/书签按钮

        Args:
            elements: 候选元素列表

        Returns:
            DecisionResult，包含选中元素、置信度、备选列表和推理说明
        """
        if not elements:
            return DecisionResult(
                selected_element=None,
                confidence=0.0,
                alternatives=[],
                reasoning="元素列表为空，无法选择收藏按钮"
            )

        valid_elements = []
        for elem in elements:
            text = self._extract_element_text(elem)
            if text:
                elem_copy = elem.copy()
                elem_copy["_extracted_text"] = text
                valid_elements.append(elem_copy)

        if not valid_elements:
            return DecisionResult(
                selected_element=None,
                confidence=0.0,
                alternatives=[],
                reasoning="没有找到包含有效文本的元素"
            )

        element_scores = []
        for elem in valid_elements:
            element_text = elem["_extracted_text"]

            best_score = 0.0
            best_target = ""

            for target in self.BOOKMARK_TARGETS:
                score = await self._calculate_similarity(element_text, target)
                if score > best_score:
                    best_score = score
                    best_target = target

            element_scores.append({
                "element": elem,
                "score": best_score,
                "matched_target": best_target,
                "text": element_text
            })

        element_scores.sort(key=lambda x: x["score"], reverse=True)

        best = element_scores[0]
        alternatives = [item["element"] for item in element_scores[1:10]]

        reasoning = f"选中元素文本: '{best['text']}'，与目标'{best['matched_target']}'的相似度为 {best['score']:.4f}"

        if len(element_scores) > 1:
            reasoning += f"，备选数量: {len(element_scores) - 1}"

        return DecisionResult(
            selected_element=best["element"],
            confidence=best["score"],
            alternatives=alternatives,
            reasoning=reasoning
        )

    async def classify_page(self, text: str) -> PageClassification:
        """
        使用Embedding对页面进行分类

        根据页面文本内容，分类为以下类型:
        - login: 登录页面
        - job_list: 职位列表页面
        - job_detail: 职位详情页面
        - popup: 弹窗页面
        - captcha: 验证码页面
        - unknown: 未知类型

        Args:
            text: 页面的文本内容

        Returns:
            PageClassification，包含页面类型、置信度和推理说明
        """
        if not text:
            return PageClassification(
                page_type="unknown",
                confidence=0.0,
                reasoning="页面文本为空，无法分类"
            )

        # 对每种页面类型计算相似度
        type_scores = {}

        for page_type, keywords in self.PAGE_TYPE_KEYWORDS.items():
            # 计算与该类型所有关键词的最高相似度
            best_score = 0.0
            best_keyword = ""

            for keyword in keywords:
                score = await self._calculate_similarity(text, keyword)
                if score > best_score:
                    best_score = score
                    best_keyword = keyword

            type_scores[page_type] = {
                "score": best_score,
                "keyword": best_keyword
            }

        # 找出得分最高的类型
        best_type = "unknown"
        best_score = 0.0
        best_keyword = ""

        for page_type, data in type_scores.items():
            if data["score"] > best_score:
                best_score = data["score"]
                best_type = page_type
                best_keyword = data["keyword"]

        reasoning = f"页面文本与'{best_keyword}'(类型:{best_type})的相似度为 {best_score:.4f}"

        # 根据置信度调整类型
        confidence = best_score
        if confidence < 0.3:
            best_type = "unknown"
            reasoning = f"所有类型匹配度较低({best_score:.4f})，判定为unknown"

        return PageClassification(
            page_type=best_type,
            confidence=confidence,
            reasoning=reasoning
        )

    async def unified_platform_match(
        self,
        platform_jobs: List[Dict],
        target_job: Dict
    ) -> List[Dict]:
        """
        统一平台匹配 - 将不同平台的职位描述映射到统一格式

        Args:
            platform_jobs: 各平台获取的原始职位列表
            target_job: 目标职位描述（统一格式）

        Returns:
            匹配后的职位列表，按相似度降序排列
        """
        if not platform_jobs or not target_job:
            return platform_jobs

        target_text = self._build_job_text(target_job)

        # 批量计算相似度
        job_texts = []
        for job in platform_jobs:
            job_text = self._build_job_text(job)
            job_texts.append(job_text)

        # 批量嵌入
        all_texts = [target_text] + job_texts
        all_embeddings = await self._embed_texts(all_texts)

        if not all_embeddings or len(all_embeddings) < len(all_texts):
            return platform_jobs

        target_embedding = all_embeddings[0]
        job_embeddings = all_embeddings[1:]

        # 计算每个职位的相似度
        scored_jobs = []
        for i, (job, embedding) in enumerate(zip(platform_jobs, job_embeddings)):
            if not embedding:
                similarity = 0.0
            else:
                similarity = self._cosine_similarity(target_embedding, embedding)
                similarity = (similarity + 1) / 2

            job_copy = job.copy()
            job_copy["_match_score"] = similarity
            scored_jobs.append((similarity, job_copy))

        # 按相似度降序排序
        scored_jobs.sort(key=lambda x: x[0], reverse=True)

        return [job for _, job in scored_jobs]

    def _build_job_text(self, job: Dict) -> str:
        """
        构建职位的统一文本描述

        Args:
            job: 职位信息字典

        Returns:
            组合后的职位文本
        """
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

        return " | ".join(parts)

    async def score_batch_elements(
        self,
        elements: List[Dict],
        target: str
    ) -> List[Dict]:
        """
        批量评分多个元素与目标短语的相关性

        Args:
            elements: 元素列表
            target: 目标短语

        Returns:
            评分后的元素列表，每个元素包含_score字段
        """
        if not elements or not target:
            return elements

        # 提取所有元素文本
        element_texts = [self._extract_element_text(elem) for elem in elements]

        # 批量嵌入
        all_texts = [target] + element_texts
        all_embeddings = await self._embed_texts(all_texts)

        if not all_embeddings or len(all_embeddings) < len(all_texts):
            return elements

        target_embedding = all_embeddings[0]
        element_embeddings = all_embeddings[1:]

        # 计算每个元素的相似度
        scored_elements = []
        for elem, embedding in zip(elements, element_embeddings):
            if not embedding:
                score = 0.0
            else:
                similarity = self._cosine_similarity(target_embedding, embedding)
                score = (similarity + 1) / 2

            elem_copy = elem.copy()
            elem_copy["_score"] = score
            scored_elements.append(elem_copy)

        # 按分数降序排序
        scored_elements.sort(key=lambda x: x["_score"], reverse=True)

        return scored_elements

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 导出主要类
__all__ = ["DecisionEngine", "DecisionResult", "PageClassification"]
