"""
基于传统图算法的知识图谱推理引擎
支持多步推理逻辑和图结构分析
"""

import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from dataclasses import dataclass
from collections import defaultdict, deque
import heapq
import math
import logging
from pathlib import Path
import json

from .models import KnowledgeGraph, KnowledgeTriple as Triple
from .config import get_config


@dataclass
class ReasoningResult:
    """推理结果"""
    answer: str
    confidence: float
    reasoning_path: List[str]
    supporting_triples: List[Triple]
    method: str
    depth: int


@dataclass
class PathResult:
    """路径查询结果"""
    path: List[str]
    length: int
    weight: float
    triples: List[Triple]


@dataclass
class CentralityResult:
    """中心性分析结果"""
    entity: str
    centrality_score: float
    rank: int
    metric_type: str


class GraphReasoner:
    """基于传统图算法的知识图谱推理引擎"""

    def __init__(self, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.knowledge_graph = knowledge_graph
        self.graph = nx.DiGraph()
        self.entity_index = {}  # 实体名称到图节点的映射
        self.reverse_entity_index = {}  # 图节点到实体名称的映射

        if knowledge_graph:
            self._build_graph()

    def _build_graph(self) -> None:
        """从知识图谱构建NetworkX图"""
        if not self.knowledge_graph:
            return

        # 清空现有图
        self.graph.clear()
        self.entity_index.clear()
        self.reverse_entity_index.clear()

        # 添加节点和边
        for i, triple in enumerate(self.knowledge_graph.triples):
            subject_id = self._get_entity_id(triple.subject)
            object_id = self._get_entity_id(triple.object)

            # 添加节点
            if subject_id not in self.graph:
                self.graph.add_node(subject_id, label=triple.subject)
            if object_id not in self.graph:
                self.graph.add_node(object_id, label=triple.object)

            # 添加边（关系）
            self.graph.add_edge(
                subject_id,
                object_id,
                relation=triple.predicate,
                weight=1.0,  # 默认权重
                triple_index=i
            )

    def _get_entity_id(self, entity_name: str) -> int:
        """获取实体ID，如果不存在则创建新的"""
        if entity_name not in self.entity_index:
            entity_id = len(self.entity_index)
            self.entity_index[entity_name] = entity_id
            self.reverse_entity_index[entity_id] = entity_name
        return self.entity_index[entity_name]

    def _get_entity_name(self, entity_id: int) -> str:
        """根据实体ID获取实体名称"""
        return self.reverse_entity_index.get(entity_id, str(entity_id))

    def update_knowledge_graph(self, knowledge_graph: KnowledgeGraph) -> None:
        """更新知识图谱并重建图"""
        self.knowledge_graph = knowledge_graph
        self._build_graph()

    # ======== 基础图遍历算法 ========

    def bfs_traversal(self, start_entity: str, max_depth: int = 3) -> List[str]:
        """广度优先搜索遍历"""
        if start_entity not in self.entity_index:
            return []

        start_id = self.entity_index[start_entity]
        visited = set()
        queue = deque([(start_id, 0)])  # (node_id, depth)
        result = []

        while queue:
            node_id, depth = queue.popleft()

            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)
            entity_name = self._get_entity_name(node_id)
            result.append(entity_name)

            # 访问邻居节点
            for neighbor in self.graph.neighbors(node_id):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

            # 也访问反向邻居（因为是有向图）
            for neighbor in self.graph.predecessors(node_id):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        return result

    def dfs_traversal(self, start_entity: str, max_depth: int = 3) -> List[str]:
        """深度优先搜索遍历"""
        if start_entity not in self.entity_index:
            return []

        start_id = self.entity_index[start_entity]
        visited = set()
        result = []

        def dfs(node_id: int, depth: int):
            if node_id in visited or depth > max_depth:
                return

            visited.add(node_id)
            entity_name = self._get_entity_name(node_id)
            result.append(entity_name)

            # 访问邻居节点
            for neighbor in self.graph.neighbors(node_id):
                dfs(neighbor, depth + 1)

            # 访问反向邻居
            for neighbor in self.graph.predecessors(node_id):
                dfs(neighbor, depth + 1)

        dfs(start_id, 0)
        return result

    # ======== 路径查找算法 ========

    def find_shortest_path(self, source: str, target: str) -> Optional[PathResult]:
        """查找两个实体之间的最短路径"""
        if source not in self.entity_index or target not in self.entity_index:
            return None

        source_id = self.entity_index[source]
        target_id = self.entity_index[target]

        try:
            # 使用NetworkX的最短路径算法
            path_ids = nx.shortest_path(self.graph, source_id, target_id)
            path_names = [self._get_entity_name(node_id) for node_id in path_ids]

            # 获取路径上的三元组
            triples = []
            for i in range(len(path_ids) - 1):
                source_node = path_ids[i]
                target_node = path_ids[i + 1]

                if self.graph.has_edge(source_node, target_node):
                    edge_data = self.graph[source_node][target_node]
                    triple_index = edge_data.get('triple_index')
                    if triple_index is not None and self.knowledge_graph:
                        triples.append(self.knowledge_graph.triples[triple_index])

            return PathResult(
                path=path_names,
                length=len(path_names) - 1,
                weight=len(path_names) - 1,  # 非权重图
                triples=triples
            )

        except nx.NetworkXNoPath:
            return None

    def find_all_paths(self, source: str, target: str, max_length: int = 5) -> List[PathResult]:
        """查找两个实体之间的所有路径（限制长度）"""
        if source not in self.entity_index or target not in self.entity_index:
            return []

        source_id = self.entity_index[source]
        target_id = self.entity_index[target]

        all_paths = []

        def dfs_find_paths(current_id: int, target_id: int, path: List[int], visited: Set[int]):
            if len(path) > max_length:
                return

            if current_id == target_id and len(path) > 1:
                # 找到一条路径
                path_names = [self._get_entity_name(node_id) for node_id in path]
                triples = []

                for i in range(len(path) - 1):
                    source_node = path[i]
                    target_node = path[i + 1]
                    if self.graph.has_edge(source_node, target_node):
                        edge_data = self.graph[source_node][target_node]
                        triple_index = edge_data.get('triple_index')
                        if triple_index is not None and self.knowledge_graph:
                            triples.append(self.knowledge_graph.triples[triple_index])

                all_paths.append(PathResult(
                    path=path_names,
                    length=len(path_names) - 1,
                    weight=len(path_names) - 1,
                    triples=triples
                ))
                return

            # 继续搜索
            for neighbor in self.graph.neighbors(current_id):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs_find_paths(neighbor, target_id, path + [neighbor], visited)
                    visited.remove(neighbor)

        visited = {source_id}
        dfs_find_paths(source_id, target_id, [source_id], visited)

        return sorted(all_paths, key=lambda x: x.length)

    # ======== 多步推理算法 ========

    def multi_step_reasoning(self, query: str, max_depth: int = 3) -> List[ReasoningResult]:
        """多步推理：A→B→C形式的推理链"""
        # 解析查询，提取实体和关系
        entities = self._extract_entities_from_query(query)
        if not entities:
            return []

        results = []

        for start_entity in entities:
            if start_entity not in self.entity_index:
                continue

            # 执行多步推理
            reasoning_chains = self._find_reasoning_chains(start_entity, max_depth)

            for chain in reasoning_chains:
                # 生成推理结果
                answer = self._generate_chain_explanation(chain)
                confidence = self._calculate_chain_confidence(chain)

                result = ReasoningResult(
                    answer=answer,
                    confidence=confidence,
                    reasoning_path=chain,
                    supporting_triples=self._get_chain_triples(chain),
                    method="multi_step_reasoning",
                    depth=len(chain) - 1
                )
                results.append(result)

        return sorted(results, key=lambda x: (x.confidence, x.depth), reverse=True)

    def _find_reasoning_chains(self, start_entity: str, max_depth: int) -> List[List[str]]:
        """查找推理链"""
        if start_entity not in self.entity_index:
            return []

        start_id = self.entity_index[start_entity]
        chains = []

        def dfs_find_chains(current_id: int, path: List[int], visited: Set[int]):
            if len(path) > max_depth + 1:  # +1 因为包括起始节点
                return

            # 如果路径长度至少为2，则作为一条推理链
            if len(path) >= 2:
                chain_names = [self._get_entity_name(node_id) for node_id in path]
                chains.append(chain_names)

            # 继续扩展链
            for neighbor in self.graph.neighbors(current_id):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs_find_chains(neighbor, path + [neighbor], visited)
                    visited.remove(neighbor)

        visited = {start_id}
        dfs_find_chains(start_id, [start_id], visited)

        # 去重并过滤
        unique_chains = []
        seen = set()
        for chain in chains:
            chain_tuple = tuple(chain)
            if chain_tuple not in seen and len(chain) <= max_depth + 1:
                seen.add(chain_tuple)
                unique_chains.append(chain)

        return unique_chains

    def _generate_chain_explanation(self, chain: List[str]) -> str:
        """生成推理链的解释"""
        if len(chain) < 2:
            return f"发现实体: {chain[0] if chain else '未知'}"

        explanation = f"推理链: {' → '.join(chain)}"

        # 添加关系信息
        if self.knowledge_graph:
            relations = []
            for i in range(len(chain) - 1):
                for triple in self.knowledge_graph.triples:
                    if triple.subject == chain[i] and triple.object == chain[i + 1]:
                        relations.append(triple.predicate)
                        break

            if relations:
                explanation += f" (关系: {' → '.join(relations)})"

        return explanation

    def _calculate_chain_confidence(self, chain: List[str]) -> float:
        """计算推理链的置信度"""
        if not chain or len(chain) < 2:
            return 0.0

        # 基于链长度计算置信度（链越短置信度越高）
        base_confidence = 1.0 / len(chain)

        # 如果有支持的三元组，提高置信度
        supporting_triples = self._get_chain_triples(chain)
        if supporting_triples:
            bonus = 0.1 * len(supporting_triples)
            base_confidence = min(1.0, base_confidence + bonus)

        return round(base_confidence, 3)

    def _get_chain_triples(self, chain: List[str]) -> List[Triple]:
        """获取推理链支持的三元组"""
        if not self.knowledge_graph or len(chain) < 2:
            return []

        triples = []
        for i in range(len(chain) - 1):
            for triple in self.knowledge_graph.triples:
                if triple.subject == chain[i] and triple.object == chain[i + 1]:
                    triples.append(triple)
                    break

        return triples

    # ======== 图结构分析算法 ========

    def calculate_centrality(self, metric: str = "betweenness") -> List[CentralityResult]:
        """计算图的中心性指标"""
        if self.graph.number_of_nodes() == 0:
            return []

        centrality_scores = {}

        if metric == "degree":
            # 度中心性
            centrality_scores = dict(self.graph.degree())
        elif metric == "in_degree":
            # 入度中心性
            centrality_scores = dict(self.graph.in_degree())
        elif metric == "out_degree":
            # 出度中心性
            centrality_scores = dict(self.graph.out_degree())
        elif metric == "betweenness":
            # 介数中心性
            centrality_scores = nx.betweenness_centrality(self.graph)
        elif metric == "closeness":
            # 接近中心性
            centrality_scores = nx.closeness_centrality(self.graph)
        elif metric == "pagerank":
            # PageRank (需要numpy和scipy)
            try:
                centrality_scores = nx.pagerank(self.graph)
            except ImportError:
                # 如果缺少依赖，使用简单的度中心性作为替代
                self.logger.warning("缺少numpy/scipy，使用度中心性替代PageRank")
                centrality_scores = dict(self.graph.degree())
        else:
            raise ValueError(f"Unsupported centrality metric: {metric}")

        # 转换为结果并排序
        results = []
        for node_id, score in centrality_scores.items():
            entity_name = self._get_entity_name(node_id)
            results.append(CentralityResult(
                entity=entity_name,
                centrality_score=round(score, 4),
                rank=0,  # 稍后计算
                metric_type=metric
            ))

        # 按分数排序并计算排名
        results.sort(key=lambda x: x.centrality_score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def find_communities(self) -> Dict[str, List[str]]:
        """发现图中的社区结构"""
        if self.graph.number_of_nodes() == 0:
            return {}

        try:
            # 使用Louvain算法检测社区
            communities = nx.community_louvain_communities(self.graph.to_undirected())

            result = {}
            for i, community in enumerate(communities):
                community_name = f"社区_{i+1}"
                community_entities = [self._get_entity_name(node_id) for node_id in community]
                result[community_name] = sorted(community_entities)

            return result

        except Exception:
            # 如果Louvain算法失败，使用简单的连通组件
            components = nx.connected_components(self.graph.to_undirected())
            result = {}

            for i, component in enumerate(components):
                component_name = f"连通组件_{i+1}"
                component_entities = [self._get_entity_name(node_id) for node_id in component]
                result[component_name] = sorted(component_entities)

            return result

    def analyze_graph_structure(self) -> Dict[str, Any]:
        """分析图的整体结构"""
        if self.graph.number_of_nodes() == 0:
            return {"error": "空图"}

        # 基础统计
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()

        # 连通性分析
        is_strongly_connected = nx.is_strongly_connected(self.graph)
        is_weakly_connected = nx.is_weakly_connected(self.graph)

        # 计算连通组件数
        num_strong_components = nx.number_strongly_connected_components(self.graph)
        num_weak_components = nx.number_weakly_connected_components(self.graph)

        # 密度
        density = nx.density(self.graph)

        # 平均路径长度（对于连通图）
        avg_path_length = None
        if nx.is_weakly_connected(self.graph):
            try:
                undirected = self.graph.to_undirected()
                avg_path_length = nx.average_shortest_path_length(undirected)
            except Exception:
                pass

        # 聚类系数
        clustering_coeff = None
        try:
            clustering_coeff = nx.average_clustering(self.graph.to_undirected())
        except Exception:
            pass

        return {
            "基本统计": {
                "节点数": num_nodes,
                "边数": num_edges,
                "密度": round(density, 4),
            },
            "连通性": {
                "强连通": is_strongly_connected,
                "弱连通": is_weakly_connected,
                "强连通组件数": num_strong_components,
                "弱连通组件数": num_weak_components,
            },
            "路径特征": {
                "平均路径长度": round(avg_path_length, 4) if avg_path_length else None,
                "聚类系数": round(clustering_coeff, 4) if clustering_coeff else None,
            },
            "中心性排名": {
                "度中心性前5": self.calculate_centrality("degree")[:5],
                "介数中心性前5": self.calculate_centrality("betweenness")[:5],
                "PageRank前5": self.calculate_centrality("pagerank")[:5],
            }
        }

    # ======== 查询处理 ========

    def query(self, question: str, max_results: int = 5) -> List[ReasoningResult]:
        """处理查询问题"""
        # 首先尝试多步推理
        reasoning_results = self.multi_step_reasoning(question)

        # 如果推理结果不足，尝试基于中心性的实体推荐
        if len(reasoning_results) < max_results:
            central_entities = self.calculate_centrality("pagerank")[:3]

            for central in central_entities:
                # 生成基于中心性实体的回答
                answer = f"重要实体: {central.entity} (PageRank: {central.centrality_score})"

                result = ReasoningResult(
                    answer=answer,
                    confidence=central.centrality_score,
                    reasoning_path=[central.entity],
                    supporting_triples=[],
                    method="centrality_analysis",
                    depth=0
                )
                reasoning_results.append(result)

        return reasoning_results[:max_results]

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """从查询中提取实体名称"""
        entities = []
        query_lower = query.lower()

        # 简单的实体提取：查找图中存在的实体
        for entity_name in self.entity_index.keys():
            if entity_name.lower() in query_lower:
                entities.append(entity_name)

        return entities

    # ======== 实用方法 ========

    def get_neighbors(self, entity: str, direction: str = "both") -> List[str]:
        """获取实体的邻居"""
        if entity not in self.entity_index:
            return []

        entity_id = self.entity_index[entity]
        neighbors = []

        if direction in ["outgoing", "both"]:
            for neighbor_id in self.graph.neighbors(entity_id):
                neighbors.append(self._get_entity_name(neighbor_id))

        if direction in ["incoming", "both"]:
            for neighbor_id in self.graph.predecessors(entity_id):
                neighbors.append(self._get_entity_name(neighbor_id))

        return list(set(neighbors))  # 去重

    def get_entity_relations(self, entity: str) -> List[Triple]:
        """获取实体的所有关系"""
        if not self.knowledge_graph or entity not in self.entity_index:
            return []

        relations = []
        for triple in self.knowledge_graph.triples:
            if triple.subject == entity or triple.object == entity:
                relations.append(triple)

        return relations

    def export_graph_analysis(self, output_path: str) -> None:
        """导出图分析结果到文件"""
        analysis = self.analyze_graph_structure()

        # 添加社区检测
        communities = self.find_communities()
        analysis["社区结构"] = communities

        # 添加中心性完整结果
        for metric in ["degree", "betweenness", "pagerank"]:
            centralities = self.calculate_centrality(metric)
            analysis[f"{metric}_中心性完整"] = [
                {"entity": c.entity, "score": c.centrality_score, "rank": c.rank}
                for c in centralities
            ]

        # 保存到文件
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        print(f"✓ 图分析结果已导出到: {output_path}")

    def visualize_graph(self, output_path: str, max_nodes: int = 50) -> None:
        """可视化图结构（需要matplotlib）"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            # 如果节点太多，只选择重要的节点
            if self.graph.number_of_nodes() > max_nodes:
                centralities = self.calculate_centrality("pagerank")[:max_nodes]
                important_entities = {c.entity for c in centralities}

                # 创建子图
                subgraph_nodes = []
                for entity in important_entities:
                    if entity in self.entity_index:
                        subgraph_nodes.append(self.entity_index[entity])

                graph_to_draw = self.graph.subgraph(subgraph_nodes)
            else:
                graph_to_draw = self.graph

            # 绘制图形
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(graph_to_draw, k=1, iterations=50)

            # 绘制节点
            nx.draw_networkx_nodes(
                graph_to_draw, pos,
                node_color='lightblue',
                node_size=500,
                alpha=0.8
            )

            # 绘制边
            nx.draw_networkx_edges(
                graph_to_draw, pos,
                edge_color='gray',
                alpha=0.6,
                arrows=True,
                arrowsize=20
            )

            # 绘制标签
            labels = {node_id: self._get_entity_name(node_id) for node_id in graph_to_draw.nodes()}
            nx.draw_networkx_labels(
                graph_to_draw, pos, labels,
                font_size=8,
                font_weight='bold'
            )

            plt.title("知识图谱结构可视化", fontsize=16)
            plt.axis('off')
            plt.tight_layout()

            # 保存图片
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            print(f"✓ 图可视化已保存到: {output_path}")

        except ImportError:
            print("⚠ 需要安装matplotlib库: pip install matplotlib")
        except Exception as e:
            print(f"✗ 可视化失败: {e}")