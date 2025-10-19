"""
LLM驱动的知识图谱推理引擎
以大模型为主体，图谱为知识库的推理架构
"""

import logging
import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI

from .models import KnowledgeGraph, KnowledgeTriple as Triple
from .config import get_config
from .graph_reasoner import GraphReasoner


class QueryIntent(Enum):
    """查询意图类型"""
    FACTUAL = "factual"          # 事实查询
    REASONING = "reasoning"      # 推理查询
    CAUSAL = "causal"           # 因果查询
    COMPARATIVE = "comparative"  # 比较查询
    PROCEDURAL = "procedural"    # 过程查询
    TEMPORAL = "temporal"        # 时间查询
    SPATIAL = "spatial"         # 空间查询


@dataclass
class SearchPlan:
    """搜索计划"""
    keywords: List[str]         # 搜索关键词
    entities: List[str]         # 目标实体
    relations: List[str]        # 目标关系
    reasoning_steps: List[str]  # 推理步骤
    search_depth: int           # 搜索深度


@dataclass
class GraphEvidence:
    """图谱证据"""
    triples: List[Triple]       # 支持三元组
    paths: List[List[str]]      # 推理路径
    confidence: float           # 证据置信度
    coverage: float             # 覆盖率


@dataclass
class LLMReasoningResult:
    """LLM推理结果"""
    answer: str
    confidence: float
    reasoning_process: List[str]
    sources: List[str]
    verification_needed: bool


class LLMDrivenReasoner:
    """LLM驱动的知识图谱推理器"""

    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        # 初始化组件
        self.llm_client = AsyncOpenAI(**self.config.get_openai_client_config())
        self.graph_reasoner = GraphReasoner(knowledge_graph)
        self.knowledge_graph = knowledge_graph

        # 推理配置
        self.max_search_depth = 3
        self.max_evidence_count = 10
        self.confidence_threshold = 0.6

    def update_knowledge_graph(self, knowledge_graph: KnowledgeGraph) -> None:
        """更新知识图谱"""
        self.knowledge_graph = knowledge_graph
        self.graph_reasoner.update_knowledge_graph(knowledge_graph)

    async def _analyze_query_intent(self, question: str) -> Tuple[QueryIntent, Dict[str, Any]]:
        """分析查询意图"""
        try:
            intent_prompt = f"""
请分析以下用户查询的意图和关键信息：

查询："{question}"

请返回JSON格式，包含：
1. intent_type: 查询意图类型
2. complexity: 复杂度 (simple/medium/complex)
3. entities: 提取的实体
4. keywords: 搜索关键词
5. expected_answer_type: 期望的答案类型
6. reasoning_required: 是否需要推理

{{
    "intent_type": "factual|reasoning|causal|comparative|procedural|temporal|spatial",
    "complexity": "simple|medium|complex",
    "entities": ["实体1", "实体2"],
    "keywords": ["关键词1", "关键词2"],
    "expected_answer_type": "definition|explanation|comparison|steps|factors",
    "reasoning_required": true/false,
    "analysis": "分析说明"
}}
"""

            response = await self.llm_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的查询意图分析专家，擅长理解用户的深层意图。"},
                    {"role": "user", "content": intent_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                extra_body={"enable_thinking": False}
            )

            content = response.choices[0].message.content

            # 解析响应
            try:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(content)

                intent = QueryIntent(result.get("intent_type", "factual"))
                return intent, result

            except json.JSONDecodeError:
                # 降级处理
                self.logger.warning(f"意图分析失败，使用默认分析: {content}")
                return QueryIntent.FACTUAL, {
                    "complexity": "medium",
                    "entities": [],
                    "keywords": [word for word in question.split() if len(word) > 1],
                    "reasoning_required": True
                }

        except Exception as e:
            self.logger.error(f"查询意图分析失败: {e}")
            return QueryIntent.FACTUAL, {
                "complexity": "medium",
                "entities": [],
                "keywords": [],
                "reasoning_required": True
            }

    async def _create_search_plan(self, question: str, intent_analysis: Dict[str, Any]) -> SearchPlan:
        """创建搜索计划"""
        try:
            plan_prompt = f"""
基于用户查询和意图分析，创建一个知识图谱搜索计划：

用户查询："{question}"
意图分析：{json.dumps(intent_analysis, ensure_ascii=False)}

请制定搜索计划，包含：
1. keywords: 主要搜索关键词（3-5个）
2. entities: 需要查找的核心实体
3. relations: 需要查找的关系类型
4. reasoning_steps: 推理步骤
5. search_depth: 搜索深度（1-3）

{{
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "entities": ["实体1", "实体2"],
    "relations": ["关系1", "关系2"],
    "reasoning_steps": [
        "第一步：查找...",
        "第二步：分析...",
        "第三步：综合..."
    ],
    "search_depth": 2,
    "strategy": "搜索策略说明"
}}
"""

            response = await self.llm_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个知识图谱搜索专家，擅长制定高效的搜索策略。"},
                    {"role": "user", "content": plan_prompt}
                ],
                temperature=0.2,
                max_tokens=600,
                extra_body={"enable_thinking": False}
            )

            content = response.choices[0].message.content

            # 解析搜索计划
            try:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group(1))
                else:
                    plan_data = json.loads(content)

                return SearchPlan(
                    keywords=plan_data.get("keywords", []),
                    entities=plan_data.get("entities", []),
                    relations=plan_data.get("relations", []),
                    reasoning_steps=plan_data.get("reasoning_steps", []),
                    search_depth=min(plan_data.get("search_depth", 2), self.max_search_depth)
                )

            except json.JSONDecodeError:
                # 降级到简单计划
                return SearchPlan(
                    keywords=intent_analysis.get("keywords", [])[:3],
                    entities=intent_analysis.get("entities", []),
                    relations=[],
                    reasoning_steps=["搜索相关信息", "分析结果", "生成答案"],
                    search_depth=2
                )

        except Exception as e:
            self.logger.error(f"搜索计划创建失败: {e}")
            return SearchPlan(
                keywords=[],
                entities=[],
                relations=[],
                reasoning_steps=["搜索相关信息"],
                search_depth=2
            )

    async def _search_knowledge_graph(self, plan: SearchPlan) -> GraphEvidence:
        """在知识图谱中搜索证据"""
        if not self.knowledge_graph:
            return GraphEvidence(triples=[], paths=[], confidence=0.0, coverage=0.0)

        all_triples = []
        all_paths = []

        try:
            # 1. 基于关键词搜索
            for keyword in plan.keywords:
                # 搜索包含关键词的三元组
                for triple in self.knowledge_graph.triples:
                    if (keyword.lower() in triple.subject.lower() or
                        keyword.lower() in triple.object.lower() or
                        keyword.lower() in triple.predicate.lower()):
                        all_triples.append(triple)

            # 2. 基于实体搜索
            for entity in plan.entities:
                # 搜索相关实体
                entity_triples = self.graph_reasoner.get_entity_relations(entity)
                all_triples.extend(entity_triples)

                # 搜索邻居
                neighbors = self.graph_reasoner.get_neighbors(entity)
                for neighbor in neighbors:
                    neighbor_triples = self.graph_reasoner.get_entity_relations(neighbor)
                    all_triples.extend(neighbor_triples)

            # 3. 基于关系搜索
            for relation in plan.relations:
                for triple in self.knowledge_graph.triples:
                    if relation.lower() in triple.predicate.lower():
                        all_triples.append(triple)

            # 4. 查找推理路径
            if len(plan.entities) >= 2:
                for i in range(len(plan.entities)):
                    for j in range(i + 1, len(plan.entities)):
                        path = self.graph_reasoner.find_shortest_path(
                            plan.entities[i], plan.entities[j]
                        )
                        if path:
                            all_paths.append(path.path)

            # 5. 多步推理链
            if plan.reasoning_steps and plan.entities:
                for entity in plan.entities:
                    reasoning_results = self.graph_reasoner.multi_step_reasoning(
                        entity, max_depth=plan.search_depth
                    )
                    for result in reasoning_results:
                        if result.reasoning_path and len(result.reasoning_path) > 1:
                            all_paths.append(result.reasoning_path)

            # 去重并排序
            unique_triples = []
            seen = set()
            for triple in all_triples:
                triple_key = (triple.subject, triple.predicate, triple.object)
                if triple_key not in seen:
                    seen.add(triple_key)
                    unique_triples.append(triple)

            # 按置信度排序
            unique_triples.sort(key=lambda x: x.confidence, reverse=True)

            # 计算置信度和覆盖率
            confidence = sum(t.confidence for t in unique_triples[:self.max_evidence_count]) / min(len(unique_triples), self.max_evidence_count)
            coverage = min(len(unique_triples) / max(len(self.knowledge_graph.triples), 1), 1.0)

            return GraphEvidence(
                triples=unique_triples[:self.max_evidence_count],
                paths=all_paths[:5],  # 限制路径数量
                confidence=confidence,
                coverage=coverage
            )

        except Exception as e:
            self.logger.error(f"知识图谱搜索失败: {e}")
            return GraphEvidence(triples=[], paths=[], confidence=0.0, coverage=0.0)

    async def _llm_reasoning_with_evidence(
        self,
        question: str,
        plan: SearchPlan,
        evidence: GraphEvidence
    ) -> LLMReasoningResult:
        """基于证据进行LLM推理"""
        try:
            # 准备证据上下文
            evidence_context = self._format_evidence(evidence)

            reasoning_prompt = f"""
你是专业的知识推理专家。请基于以下知识图谱证据，回答用户问题。

用户问题：{question}

搜索策略：
{json.dumps({
    "keywords": plan.keywords,
    "entities": plan.entities,
    "reasoning_steps": plan.reasoning_steps
}, ensure_ascii=False, indent=2)}

知识图谱证据：
{evidence_context}

请基于证据进行推理，并提供：
1. 基于证据的准确回答
2. 详细的推理过程
3. 证据来源说明
4. 答案置信度评估
5. 是否需要额外验证

请返回JSON格式：
{{
    "answer": "详细回答",
    "confidence": 0.85,
    "reasoning_process": [
        "步骤1：分析问题",
        "步骤2：查找证据",
        "步骤3：推理分析",
        "步骤4：得出结论"
    ],
    "sources": ["证据来源1", "证据来源2"],
    "verification_needed": false,
    "evidence_quality": "high/medium/low",
    "limitations": "可能的局限性"
}}
"""

            response = await self.llm_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个严谨的知识推理专家，擅长基于结构化证据进行逻辑推理。"},
                    {"role": "user", "content": reasoning_prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                extra_body={"enable_thinking": False}
            )

            content = response.choices[0].message.content

            # 解析推理结果
            try:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(content)

                # 调整置信度（结合证据置信度）
                llm_confidence = float(result.get("confidence", 0.5))
                evidence_confidence = evidence.confidence
                final_confidence = (llm_confidence * 0.7 + evidence_confidence * 0.3)

                return LLMReasoningResult(
                    answer=result.get("answer", "无法生成回答"),
                    confidence=final_confidence,
                    reasoning_process=result.get("reasoning_process", []),
                    sources=result.get("sources", []),
                    verification_needed=result.get("verification_needed", False)
                )

            except json.JSONDecodeError:
                # 降级处理
                return LLMReasoningResult(
                    answer=content,
                    confidence=evidence.confidence,
                    reasoning_process=["基于证据分析", "生成回答"],
                    sources=[],
                    verification_needed=True
                )

        except Exception as e:
            self.logger.error(f"LLM推理失败: {e}")
            return LLMReasoningResult(
                answer=f"推理过程中出现错误: {e}",
                confidence=0.0,
                reasoning_process=[],
                sources=[],
                verification_needed=True
            )

    def _format_evidence(self, evidence: GraphEvidence) -> str:
        """格式化证据信息"""
        if not evidence.triples:
            return "未找到相关证据"

        evidence_text = "【相关三元组证据】\n"
        for i, triple in enumerate(evidence.triples[:5], 1):
            evidence_text += f"{i}. {triple.subject} --{triple.predicate}--> {triple.object} (置信度: {triple.confidence:.2f})\n"

        if evidence.paths:
            evidence_text += "\n【推理路径证据】\n"
            for i, path in enumerate(evidence.paths[:3], 1):
                evidence_text += f"{i}. {' → '.join(path)}\n"

        evidence_text += f"\n证据质量评估：置信度 {evidence.confidence:.2f}, 覆盖率 {evidence.coverage:.2f}"

        return evidence_text

    async def query(self, question: str, knowledge_graph: KnowledgeGraph) -> LLMReasoningResult:
        """LLM驱动的查询推理"""
        import time
        start_time = time.time()

        try:
            self.logger.info(f"开始LLM驱动推理: {question}")
            self.update_knowledge_graph(knowledge_graph)

            # 1. 分析查询意图
            intent, intent_analysis = await self._analyze_query_intent(question)
            self.logger.info(f"查询意图: {intent.value}, 复杂度: {intent_analysis.get('complexity')}")

            # 2. 创建搜索计划
            plan = await self._create_search_plan(question, intent_analysis)
            self.logger.info(f"搜索计划: {len(plan.keywords)} 关键词, {len(plan.entities)} 实体")

            # 3. 搜索知识图谱证据
            evidence = await self._search_knowledge_graph(plan)
            self.logger.info(f"找到证据: {len(evidence.triples)} 三元组, {len(evidence.paths)} 路径")

            # 4. LLM推理
            result = await self._llm_reasoning_with_evidence(question, plan, evidence)
            result.processing_time = time.time() - start_time

            self.logger.info(f"LLM推理完成，置信度: {result.confidence:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"LLM驱动推理失败: {e}")
            return LLMReasoningResult(
                answer=f"推理过程中出现错误: {e}",
                confidence=0.0,
                reasoning_process=[],
                sources=[],
                verification_needed=True
            )

    # 同步方法
    def query_sync(self, question: str, knowledge_graph: KnowledgeGraph) -> LLMReasoningResult:
        """同步版本的查询方法"""
        return asyncio.run(self.query(question, knowledge_graph))

    async def verify_answer(self, question: str, answer: str, knowledge_graph: KnowledgeGraph) -> Dict[str, Any]:
        """验证答案的准确性"""
        try:
            verification_prompt = f"""
请验证以下答案的准确性，基于知识图谱证据：

问题：{question}
答案：{answer}

请在知识图谱中查找支持或反驳该答案的证据，并评估：
1. 答案的准确性
2. 证据支持度
3. 可能的错误或遗漏
4. 改进建议

请返回JSON格式：
{{
    "accuracy_score": 0.85,
    "evidence_support": "strong/moderate/weak",
    "verification_result": "verified/partially_verified/incorrect",
    "corrections": ["需要修正的内容"],
    "missing_information": ["遗漏的信息"],
    "overall_assessment": "总体评估"
}}
"""

            response = await self.llm_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的知识验证专家，擅长评估信息的准确性。"},
                    {"role": "user", "content": verification_prompt}
                ],
                temperature=0.1,
                max_tokens=800,
                extra_body={"enable_thinking": False}
            )

            content = response.choices[0].message.content

            try:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                else:
                    return json.loads(content)
            except json.JSONDecodeError:
                return {"verification_result": "parsing_error", "content": content}

        except Exception as e:
            self.logger.error(f"答案验证失败: {e}")
            return {"verification_result": "error", "error": str(e)}