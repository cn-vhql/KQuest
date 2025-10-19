"""知识推理模块 - 基于传统图算法的推理引擎"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import json
from difflib import SequenceMatcher

from .config import get_config
from .models import (
    KnowledgeGraph,
    KnowledgeTriple,
    QueryResult,
    TripleType,
)
from .graph_reasoner import GraphReasoner, ReasoningResult, PathResult, CentralityResult


class KnowledgeReasoner:
    """基于传统图算法的知识推理器"""

    def __init__(self, config=None, knowledge_graph: Optional[KnowledgeGraph] = None):
        """初始化知识推理器

        Args:
            config: 配置对象，如果为None则使用全局配置
            knowledge_graph: 知识图谱对象
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)

        # 初始化图推理引擎
        self.graph_reasoner = GraphReasoner(knowledge_graph)
    
    def update_knowledge_graph(self, knowledge_graph: KnowledgeGraph) -> None:
        """更新知识图谱

        Args:
            knowledge_graph: 新的知识图谱
        """
        self.graph_reasoner.update_knowledge_graph(knowledge_graph)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（用于向后兼容）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度分数（0-1）
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _find_similar_entities(self, entity: str, entity_list: List[str], threshold: float = 0.7) -> List[Tuple[str, float]]:
        """查找相似实体（用于向后兼容）

        Args:
            entity: 目标实体
            entity_list: 实体列表
            threshold: 相似度阈值

        Returns:
            相似实体列表，包含实体名和相似度
        """
        similar_entities = []
        for candidate in entity_list:
            similarity = self._calculate_similarity(entity, candidate)
            if similarity >= threshold:
                similar_entities.append((candidate, similarity))

        # 按相似度排序
        similar_entities.sort(key=lambda x: x[1], reverse=True)
        return similar_entities

    def _extract_entities_from_question(self, question: str) -> List[str]:
        """从问题中提取实体

        Args:
            question: 用户问题

        Returns:
            实体列表
        """
        # 提取引号内的内容
        quoted_entities = re.findall(r'["""]([^"""]+)["""]', question)

        # 提取可能的关键词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', question)

        # 过滤掉常见的停用词
        stop_words = {'是', '的', '有', '在', '和', '与', '或', '但', '而', '了', '吗', '呢', '吧', '什么', '谁', '哪里', '什么时候', '为什么', '如何', '怎么', 'the', 'is', 'are', 'what', 'who', 'where', 'when', 'why', 'how'}

        entities = []
        for word in words:
            if len(word) > 1 and word not in stop_words:
                entities.append(word)

        # 合并结果，去重
        all_entities = list(set(quoted_entities + entities))
        return all_entities

    def _find_relevant_triples(
        self,
        question: str,
        knowledge_graph: KnowledgeGraph
    ) -> List[KnowledgeTriple]:
        """查找相关的三元组（基于图算法）

        Args:
            question: 用户问题
            knowledge_graph: 知识图谱

        Returns:
            相关三元组列表
        """
        # 提取问题中的实体
        entities = self._extract_entities_from_question(question)
        relevant_triples = []

        if self.config.reasoning.enable_fuzzy_matching:
            # 模糊匹配
            all_subjects = list(set(triple.subject for triple in knowledge_graph.triples))
            all_objects = list(set(triple.object for triple in knowledge_graph.triples))

            for entity in entities:
                # 查找相似的主语
                similar_subjects = self._find_similar_entities(
                    entity, all_subjects, self.config.reasoning.similarity_threshold
                )

                # 查找相似的宾语
                similar_objects = self._find_similar_entities(
                    entity, all_objects, self.config.reasoning.similarity_threshold
                )

                # 收集相关的三元组
                for triple in knowledge_graph.triples:
                    if (any(triple.subject == subj for subj, _ in similar_subjects) or
                        any(triple.object == obj for obj, _ in similar_objects)):
                        relevant_triples.append(triple)
        else:
            # 精确匹配
            for triple in knowledge_graph.triples:
                for entity in entities:
                    if (entity in triple.subject or
                        entity in triple.object or
                        entity in triple.predicate):
                        relevant_triples.append(triple)
                        break

        # 去重并限制数量
        unique_triples = list({(t.subject, t.predicate, t.object): t for t in relevant_triples}.values())
        unique_triples.sort(key=lambda x: x.confidence, reverse=True)
        return unique_triples[:self.config.reasoning.max_triples_per_query]
    
    def _perform_reasoning_graph(
        self,
        question: str,
        relevant_triples: List[KnowledgeTriple]
    ) -> Dict[str, Any]:
        """基于图算法执行推理过程

        Args:
            question: 用户问题
            relevant_triples: 相关三元组

        Returns:
            推理结果
        """
        try:
            # 使用图推理引擎处理查询
            reasoning_results = self.graph_reasoner.query(question, max_results=3)

            if not reasoning_results:
                return {
                    "answer": "抱歉，在知识图谱中没有找到与您的问题相关的信息。",
                    "confidence": 0.0,
                    "reasoning_steps": ["未找到相关信息"],
                    "source_triples": [],
                    "additional_info": ""
                }

            # 取最佳结果
            best_result = reasoning_results[0]

            # 转换三元组格式
            source_triples = []
            for triple in best_result.supporting_triples:
                source_triples.append({
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object
                })

            return {
                "answer": best_result.answer,
                "confidence": best_result.confidence,
                "reasoning_steps": best_result.reasoning_path,
                "source_triples": source_triples,
                "additional_info": f"推理方法: {best_result.method}, 深度: {best_result.depth}"
            }

        except Exception as e:
            self.logger.error(f"图推理失败: {e}")
            return {
                "answer": f"图推理过程中出现错误: {e}",
                "confidence": 0.0,
                "reasoning_steps": ["推理失败"],
                "source_triples": [],
                "additional_info": ""
            }
    
    def query(
        self,
        question: str,
        knowledge_graph: KnowledgeGraph
    ) -> QueryResult:
        """基于图算法查询知识图谱并回答问题

        Args:
            question: 用户问题
            knowledge_graph: 知识图谱

        Returns:
            查询结果
        """
        start_time = time.time()

        try:
            self.logger.info(f"开始图查询问题: {question}")

            # 更新图推理引擎的知识图谱
            self.graph_reasoner.update_knowledge_graph(knowledge_graph)

            # 查找相关三元组
            relevant_triples = self._find_relevant_triples(question, knowledge_graph)

            if not relevant_triples:
                self.logger.warning("未找到相关的三元组")
                return QueryResult(
                    question=question,
                    answer="抱歉，在知识图谱中没有找到与您的问题相关的信息。",
                    confidence=0.0,
                    source_triples=[],
                    reasoning_path=["未找到相关信息"],
                    metadata={"processing_time": time.time() - start_time}
                )

            self.logger.info(f"找到{len(relevant_triples)}个相关三元组")

            # 执行图推理
            reasoning_result = self._perform_reasoning_graph(question, relevant_triples)

            # 构建查询结果
            query_result = QueryResult(
                question=question,
                answer=reasoning_result.get("answer", "无法生成回答"),
                confidence=float(reasoning_result.get("confidence", 0.5)),
                reasoning_path=reasoning_result.get("reasoning_steps", []),
                metadata={
                    "processing_time": time.time() - start_time,
                    "relevant_triples_count": len(relevant_triples),
                    "additional_info": reasoning_result.get("additional_info", ""),
                    "method": "graph_algorithm"
                }
            )

            # 添加来源三元组
            for triple_data in reasoning_result.get("source_triples", []):
                for triple in relevant_triples:
                    if (triple.subject == triple_data.get("subject") and
                        triple.predicate == triple_data.get("predicate") and
                        triple.object == triple_data.get("object")):
                        query_result.add_source_triple(triple)
                        break

            self.logger.info(f"图查询完成，置信度: {query_result.confidence}")
            return query_result

        except Exception as e:
            error_msg = f"图查询失败: {e}"
            self.logger.error(error_msg)

            return QueryResult(
                question=question,
                answer=f"图查询过程中出现错误: {e}",
                confidence=0.0,
                source_triples=[],
                reasoning_path=["查询失败"],
                metadata={
                    "processing_time": time.time() - start_time,
                    "error": str(e)
                }
            )
    
    def infer_new_knowledge(self, knowledge_graph: KnowledgeGraph) -> List[KnowledgeTriple]:
        """基于图算法推理新知识

        Args:
            knowledge_graph: 现有知识图谱

        Returns:
            推理出的新三元组列表
        """
        try:
            self.logger.info("开始基于图算法推理新知识")

            # 更新图推理引擎
            self.graph_reasoner.update_knowledge_graph(knowledge_graph)

            # 执行多步推理
            all_entities = list(set(self.graph_reasoner.entity_index.keys()))
            inferred_triples = []

            # 对每个重要实体进行推理
            central_entities = self.graph_reasoner.calculate_centrality("pagerank")[:10]

            for central in central_entities:
                entity = central.entity
                # 找到推理链
                reasoning_results = self.graph_reasoner.multi_step_reasoning(entity, max_depth=2)

                for result in reasoning_results:
                    if result.confidence > 0.5 and len(result.reasoning_path) >= 2:
                        # 从推理路径创建新的三元组
                        for i in range(len(result.reasoning_path) - 1):
                            subject = result.reasoning_path[i]
                            object = result.reasoning_path[i + 1]

                            # 查找或推断关系
                            relation = self._infer_relation(subject, object, knowledge_graph)
                            if relation:
                                new_triple = KnowledgeTriple(
                                    subject=subject,
                                    predicate=relation,
                                    object=object,
                                    triple_type=TripleType.ENTITY_RELATION,
                                    confidence=result.confidence,
                                    metadata={
                                        "inferred": True,
                                        "reasoning": f"多步推理: {' → '.join(result.reasoning_path)}",
                                        "method": "graph_algorithm",
                                        "depth": result.depth
                                    }
                                )
                                inferred_triples.append(new_triple)

            # 去重
            unique_triples = []
            seen = set()
            for triple in inferred_triples:
                triple_key = (triple.subject, triple.predicate, triple.object)
                if triple_key not in seen:
                    seen.add(triple_key)
                    unique_triples.append(triple)

            self.logger.info(f"图算法推理出{len(unique_triples)}个新三元组")
            return unique_triples

        except Exception as e:
            self.logger.error(f"图算法推理新知识失败: {e}")
            return []

    def _infer_relation(self, subject: str, object: str, knowledge_graph: KnowledgeGraph) -> Optional[str]:
        """推断两个实体之间的关系

        Args:
            subject: 主语实体
            object: 宾语实体
            knowledge_graph: 知识图谱

        Returns:
            推断的关系名称
        """
        # 查找已知关系
        for triple in knowledge_graph.triples:
            if triple.subject == subject and triple.object == object:
                return triple.predicate

        # 查找相似的实体对
        similar_relations = {}
        for triple in knowledge_graph.triples:
            if triple.subject == subject:
                similar_relations[triple.predicate] = similar_relations.get(triple.predicate, 0) + 1
            elif triple.object == object:
                similar_relations[triple.predicate] = similar_relations.get(triple.predicate, 0) + 1

        if similar_relations:
            return max(similar_relations, key=similar_relations.get)

        # 默认关系
        return "相关于"

    def query_sync(self, question: str, knowledge_graph: KnowledgeGraph) -> QueryResult:
        """同步版本的查询方法（向后兼容）

        Args:
            question: 用户问题
            knowledge_graph: 知识图谱

        Returns:
            查询结果
        """
        return self.query(question, knowledge_graph)

    def infer_new_knowledge_sync(self, knowledge_graph: KnowledgeGraph) -> List[KnowledgeTriple]:
        """同步版本的知识推理方法（向后兼容）

        Args:
            knowledge_graph: 现有知识图谱

        Returns:
            推理出的新三元组列表
        """
        return self.infer_new_knowledge(knowledge_graph)
    
    def get_graph_statistics(self, knowledge_graph: KnowledgeGraph) -> Dict[str, Any]:
        """获取知识图谱统计信息（基于图算法）

        Args:
            knowledge_graph: 知识图谱

        Returns:
            统计信息
        """
        # 更新图推理引擎
        self.graph_reasoner.update_knowledge_graph(knowledge_graph)

        # 使用图分析获取统计信息
        graph_analysis = self.graph_reasoner.analyze_graph_structure()

        # 添加传统统计信息
        basic_stats = knowledge_graph.get_statistics()
        subjects = knowledge_graph.get_subjects()
        objects = knowledge_graph.get_objects()
        predicates = knowledge_graph.get_predicates()

        # 计算连通性
        all_entities = set(subjects + objects)
        connected_entities = set()

        for triple in knowledge_graph.triples:
            connected_entities.add(triple.subject)
            connected_entities.add(triple.object)

        basic_stats.update({
            "total_entities": len(all_entities),
            "connected_entities": len(connected_entities),
            "connectivity_ratio": len(connected_entities) / len(all_entities) if all_entities else 0,
            "avg_triples_per_entity": len(knowledge_graph.triples) / len(all_entities) if all_entities else 0,
            "most_common_predicates": self._get_most_common_items(predicates, 5),
            "most_common_subjects": self._get_most_common_items(subjects, 5),
            "most_common_objects": self._get_most_common_items(objects, 5),
        })

        # 合并图分析结果
        combined_stats = {
            "基础统计": basic_stats,
            "图结构分析": graph_analysis,
            "分析方法": "传统图算法"
        }

        return combined_stats

    def _get_most_common_items(self, items: List[str], top_n: int = 5) -> List[Tuple[str, int]]:
        """获取最常见的项目

        Args:
            items: 项目列表
            top_n: 返回前N个

        Returns:
            (项目, 频次) 列表
        """
        from collections import Counter
        counter = Counter(items)
        return counter.most_common(top_n)

    # ======== 新增的图算法方法 ========

    def find_shortest_path(self, source: str, target: str) -> Optional[PathResult]:
        """查找两个实体之间的最短路径

        Args:
            source: 源实体
            target: 目标实体

        Returns:
            路径结果
        """
        return self.graph_reasoner.find_shortest_path(source, target)

    def find_all_paths(self, source: str, target: str, max_length: int = 5) -> List[PathResult]:
        """查找两个实体之间的所有路径

        Args:
            source: 源实体
            target: 目标实体
            max_length: 最大路径长度

        Returns:
            路径结果列表
        """
        return self.graph_reasoner.find_all_paths(source, target, max_length)

    def bfs_traversal(self, start_entity: str, max_depth: int = 3) -> List[str]:
        """广度优先搜索遍历

        Args:
            start_entity: 起始实体
            max_depth: 最大深度

        Returns:
            遍历的实体列表
        """
        return self.graph_reasoner.bfs_traversal(start_entity, max_depth)

    def dfs_traversal(self, start_entity: str, max_depth: int = 3) -> List[str]:
        """深度优先搜索遍历

        Args:
            start_entity: 起始实体
            max_depth: 最大深度

        Returns:
            遍历的实体列表
        """
        return self.graph_reasoner.dfs_traversal(start_entity, max_depth)

    def calculate_centrality(self, metric: str = "betweenness") -> List[CentralityResult]:
        """计算图的中心性指标

        Args:
            metric: 中心性指标类型 ("degree", "betweenness", "closeness", "pagerank")

        Returns:
            中心性结果列表
        """
        return self.graph_reasoner.calculate_centrality(metric)

    def find_communities(self) -> Dict[str, List[str]]:
        """发现图中的社区结构

        Returns:
            社区字典
        """
        return self.graph_reasoner.find_communities()

    def get_neighbors(self, entity: str, direction: str = "both") -> List[str]:
        """获取实体的邻居

        Args:
            entity: 实体名称
            direction: 方向 ("incoming", "outgoing", "both")

        Returns:
            邻居实体列表
        """
        return self.graph_reasoner.get_neighbors(entity, direction)

    def multi_step_reasoning(self, query: str, max_depth: int = 3) -> List[ReasoningResult]:
        """多步推理

        Args:
            query: 查询内容
            max_depth: 最大推理深度

        Returns:
            推理结果列表
        """
        return self.graph_reasoner.multi_step_reasoning(query, max_depth)

    def export_graph_analysis(self, output_path: str) -> None:
        """导出图分析结果到文件

        Args:
            output_path: 输出文件路径
        """
        self.graph_reasoner.export_graph_analysis(output_path)

    def visualize_graph(self, output_path: str, max_nodes: int = 50) -> None:
        """可视化图结构

        Args:
            output_path: 输出图片路径
            max_nodes: 最大显示节点数
        """
        self.graph_reasoner.visualize_graph(output_path, max_nodes)
