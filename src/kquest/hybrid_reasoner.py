"""
混合推理引擎 - 结合LLM语义理解和图算法结构推理
"""

import logging
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from openai import AsyncOpenAI

from .models import KnowledgeGraph, KnowledgeTriple as Triple
from .config import get_config
from .graph_reasoner import GraphReasoner, ReasoningResult, PathResult


@dataclass
class HybridReasoningResult:
    """混合推理结果"""
    answer: str
    confidence: float
    reasoning_method: str
    graph_paths: List[str]
    semantic_insights: List[str]
    supporting_triples: List[Triple]
    llm_enhancement: Optional[str]
    processing_time: float


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    entities: List[str]
    intent_type: str  # "factual", "causal", "comparative", "procedural"
    complexity: str   # "simple", "medium", "complex"
    requires_llm: bool


class HybridReasoner:
    """混合推理引擎"""

    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        # 初始化两个推理引擎
        self.graph_reasoner = GraphReasoner(knowledge_graph)
        self.llm_client = AsyncOpenAI(**self.config.get_openai_client_config())

        # 推理策略配置
        self.strategies = {
            "simple_factual": {"use_graph": True, "use_llm": False, "weight": 0.8},
            "complex_reasoning": {"use_graph": True, "use_llm": True, "weight": 0.6},
            "semantic_query": {"use_graph": False, "use_llm": True, "weight": 0.9},
            "path_finding": {"use_graph": True, "use_llm": True, "weight": 0.7},
            "comparative": {"use_graph": True, "use_llm": True, "weight": 0.5}
        }

    def update_knowledge_graph(self, knowledge_graph: KnowledgeGraph) -> None:
        """更新知识图谱"""
        self.graph_reasoner.update_knowledge_graph(knowledge_graph)

    async def _analyze_query(self, question: str) -> QueryAnalysis:
        """分析查询类型和复杂度"""
        try:
            # 使用LLM分析查询意图
            analysis_prompt = f"""
请分析以下用户查询的类型和复杂度：

查询："{question}"

请返回JSON格式：
{{
    "entities": ["提取出的实体1", "实体2"],
    "intent_type": "factual|causal|comparative|procedural",
    "complexity": "simple|medium|complex",
    "requires_llm": true/false,
    "reasoning": "分析原因"
}}
"""

            response = await self.llm_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个查询分析专家，擅长理解用户意图。"},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                extra_body={"enable_thinking": False}
            )

            content = response.choices[0].message.content

            # 解析LLM响应
            try:
                # 尝试直接解析JSON
                analysis_data = json.loads(content)
            except json.JSONDecodeError:
                # 提取JSON代码块
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(1))
                else:
                    # 降级到简单分析
                    analysis_data = self._simple_query_analysis(question)

            return QueryAnalysis(
                entities=analysis_data.get("entities", []),
                intent_type=analysis_data.get("intent_type", "factual"),
                complexity=analysis_data.get("complexity", "medium"),
                requires_llm=analysis_data.get("requires_llm", False)
            )

        except Exception as e:
            self.logger.warning(f"LLM查询分析失败: {e}，使用简单分析")
            return self._simple_query_analysis(question)

    def _simple_query_analysis(self, question: str) -> QueryAnalysis:
        """简单查询分析（降级方案）"""
        # 提取关键词作为实体
        import re
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', question)
        entities = [w for w in words if len(w) > 1]

        # 简单启发式判断
        question_lower = question.lower()
        if any(word in question_lower for word in ['什么', '什么是', 'what is']):
            intent_type = "factual"
        elif any(word in question_lower for word in ['为什么', 'why', '如何', 'how']):
            intent_type = "causal"
        elif any(word in question_lower for word in ['比较', '对比', 'compare']):
            intent_type = "comparative"
        else:
            intent_type = "procedural"

        complexity = "simple" if len(entities) <= 2 else "complex"
        requires_llm = complexity == "complex" or intent_type in ["causal", "comparative"]

        return QueryAnalysis(
            entities=entities,
            intent_type=intent_type,
            complexity=complexity,
            requires_llm=requires_llm
        )

    async def _graph_based_reasoning(self, question: str, query_analysis: QueryAnalysis) -> List[ReasoningResult]:
        """基于图算法的推理"""
        try:
            # 使用图推理引擎
            results = self.graph_reasoner.query(question, max_results=5)
            return results
        except Exception as e:
            self.logger.error(f"图推理失败: {e}")
            return []

    async def _llm_based_reasoning(self, question: str, relevant_triples: List[Triple]) -> Dict[str, Any]:
        """基于LLM的语义推理"""
        if not relevant_triples:
            return {
                "answer": "抱歉，没有找到相关信息来回答您的问题。",
                "confidence": 0.0,
                "insights": []
            }

        try:
            # 准备三元组上下文
            triples_text = "\n".join([
                f"- {triple.subject} -> {triple.predicate} -> {triple.object}"
                for triple in relevant_triples[:10]  # 限制数量
            ])

            reasoning_prompt = f"""
基于以下知识图谱三元组，请回答用户问题：

知识图谱信息：
{triples_text}

用户问题：{question}

请提供：
1. 基于已知信息的直接回答
2. 语义推理和常识补充
3. 回答的置信度评估

请返回JSON格式：
{{
    "answer": "详细回答",
    "confidence": 0.8,
    "insights": ["推理洞察1", "推理洞察2"],
    "reasoning": "推理过程说明"
}}
"""

            response = await self.llm_client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个知识推理专家，擅长基于结构化知识进行语义推理。"},
                    {"role": "user", "content": reasoning_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
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
            except json.JSONDecodeError:
                result = {
                    "answer": content,
                    "confidence": 0.5,
                    "insights": ["LLM推理完成"],
                    "reasoning": "基于语义理解的推理"
                }

            return result

        except Exception as e:
            self.logger.error(f"LLM推理失败: {e}")
            return {
                "answer": f"推理过程中出现错误: {e}",
                "confidence": 0.0,
                "insights": [],
                "reasoning": "推理失败"
            }

    async def _path_enhanced_reasoning(self, entities: List[str]) -> List[PathResult]:
        """路径增强推理"""
        paths = []

        if len(entities) >= 2:
            # 查找实体间的路径
            for i in range(len(entities)):
                for j in range(i + 1, min(i + 3, len(entities))):  # 限制比较数量
                    path = self.graph_reasoner.find_shortest_path(entities[i], entities[j])
                    if path and path.length <= 4:  # 限制路径长度
                        paths.append(path)

        return paths

    async def _synthesize_results(
        self,
        question: str,
        graph_results: List[ReasoningResult],
        llm_result: Dict[str, Any],
        paths: List[PathResult],
        query_analysis: QueryAnalysis
    ) -> HybridReasoningResult:
        """综合多种推理结果"""

        # 基础置信度计算
        graph_confidence = max([r.confidence for r in graph_results], default=0.0)
        llm_confidence = llm_result.get("confidence", 0.0)

        # 根据查询类型调整权重
        if query_analysis.intent_type == "factual":
            final_confidence = graph_confidence * 0.7 + llm_confidence * 0.3
        elif query_analysis.intent_type in ["causal", "comparative"]:
            final_confidence = graph_confidence * 0.4 + llm_confidence * 0.6
        else:
            final_confidence = graph_confidence * 0.5 + llm_confidence * 0.5

        # 构建回答
        if graph_results and llm_result.get("confidence", 0) > 0.5:
            # 混合回答
            primary_answer = graph_results[0].answer if graph_results else ""
            llm_enhancement = llm_result.get("answer", "")

            if primary_answer and llm_enhancement and primary_answer != llm_enhancement:
                answer = f"{primary_answer}\n\n💡 深度分析：{llm_enhancement}"
            else:
                answer = primary_answer or llm_enhancement
        elif graph_results:
            answer = graph_results[0].answer
        else:
            answer = llm_result.get("answer", "抱歉，无法回答您的问题。")

        # 提取支持信息
        supporting_triples = []
        for result in graph_results:
            supporting_triples.extend(result.supporting_triples)

        # 构建路径信息
        graph_paths = []
        for path in paths:
            graph_paths.append(" → ".join(path.path))

        # 提取语义洞察
        semantic_insights = llm_result.get("insights", [])

        # 确定推理方法
        if graph_results and llm_result.get("confidence", 0) > 0.5:
            reasoning_method = "混合推理（图算法 + LLM语义理解）"
        elif graph_results:
            reasoning_method = "图算法推理"
        else:
            reasoning_method = "LLM语义推理"

        return HybridReasoningResult(
            answer=answer,
            confidence=min(1.0, final_confidence),
            reasoning_method=reasoning_method,
            graph_paths=graph_paths,
            semantic_insights=semantic_insights,
            supporting_triples=supporting_triples[:10],  # 限制数量
            llm_enhancement=llm_result.get("answer") if llm_result.get("confidence", 0) > 0.5 else None,
            processing_time=0.0  # 实际使用时需要计算
        )

    async def query(self, question: str, knowledge_graph: KnowledgeGraph) -> HybridReasoningResult:
        """混合推理查询"""
        import time
        start_time = time.time()

        try:
            self.logger.info(f"开始混合推理查询: {question}")

            # 更新知识图谱
            self.update_knowledge_graph(knowledge_graph)

            # 1. 分析查询
            query_analysis = await self._analyze_query(question)
            self.logger.info(f"查询分析: {query_analysis.intent_type}, {query_analysis.complexity}")

            # 2. 图算法推理
            graph_results = await self._graph_based_reasoning(question, query_analysis)
            self.logger.info(f"图推理结果: {len(graph_results)} 个")

            # 3. 路径增强推理
            paths = []
            if query_analysis.entities and len(query_analysis.entities) >= 2:
                paths = await self._path_enhanced_reasoning(query_analysis.entities)
                self.logger.info(f"路径推理: {len(paths)} 条路径")

            # 4. LLM语义推理（如果需要）
            llm_result = {}
            if query_analysis.requires_llm or not graph_results:
                relevant_triples = []
                for result in graph_results:
                    relevant_triples.extend(result.supporting_triples)

                llm_result = await self._llm_based_reasoning(question, relevant_triples)
                self.logger.info(f"LLM推理完成，置信度: {llm_result.get('confidence', 0):.2f}")

            # 5. 综合结果
            final_result = await self._synthesize_results(
                question, graph_results, llm_result, paths, query_analysis
            )

            final_result.processing_time = time.time() - start_time
            self.logger.info(f"混合推理完成，置信度: {final_result.confidence:.2f}")

            return final_result

        except Exception as e:
            self.logger.error(f"混合推理失败: {e}")
            return HybridReasoningResult(
                answer=f"推理过程中出现错误: {e}",
                confidence=0.0,
                reasoning_method="错误",
                graph_paths=[],
                semantic_insights=[],
                supporting_triples=[],
                llm_enhancement=None,
                processing_time=time.time() - start_time
            )

    # 同步方法（向后兼容）
    def query_sync(self, question: str, knowledge_graph: KnowledgeGraph) -> HybridReasoningResult:
        """同步版本的查询方法"""
        import asyncio
        return asyncio.run(self.query(question, knowledge_graph))