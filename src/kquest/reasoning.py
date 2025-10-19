"""知识推理模块"""

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import json
from difflib import SequenceMatcher

import openai
from openai import AsyncOpenAI

from .config import get_config
from .models import (
    KnowledgeGraph,
    KnowledgeTriple,
    QueryResult,
    TripleType,
)


class KnowledgeReasoner:
    """知识推理器"""
    
    def __init__(self, config=None):
        """初始化知识推理器
        
        Args:
            config: 配置对象，如果为None则使用全局配置
        """
        self.config = config or get_config()
        self.client = AsyncOpenAI(**self.config.get_openai_client_config())
        self.logger = logging.getLogger(__name__)
        
        # 加载提示词模板
        self._load_prompts()
    
    def _load_prompts(self):
        """加载提示词模板"""
        # 暂时强制使用默认模板以避免YAML解析问题
        self.prompts = self._get_default_prompts()
        return
        
        try:
            from pathlib import Path
            prompts_path = Path(self.config.config_dir) / "prompts.yaml"
            if prompts_path.exists():
                import yaml
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    self.prompts = yaml.safe_load(f)
            else:
                self.prompts = self._get_default_prompts()
        except Exception as e:
            self.logger.warning(f"加载提示词模板失败: {e}，使用默认模板")
            self.prompts = self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """获取默认提示词模板"""
        return {
            "query": """你是一个专业的知识图谱推理专家。基于给定的知识图谱三元组和用户问题，提供准确、详细的回答。

知识图谱三元组：
{triples}

用户问题：{question}

请按照以下步骤进行推理：
1. 分析问题意图和关键实体
2. 在知识图谱中查找相关的三元组
3. 进行逻辑推理，找出隐含的关系
4. 综合信息给出完整回答

请以JSON格式返回结果：
```json
{{
  "answer": "详细回答",
  "confidence": 0.9,
  "reasoning_steps": [
    "推理步骤1",
    "推理步骤2"
  ],
  "source_triples": [
    {{
      "subject": "主语",
      "predicate": "谓语",
      "object": "宾语"
    }}
  ],
  "additional_info": "补充信息"
}}
```

请开始推理：""",
            
            "similarity": """请评估以下两个概念的语义相似度：

概念1：{concept1}
概念2：{concept2}

请返回0.0-1.0之间的相似度分数，并简要说明理由。

请以JSON格式返回：
```json
{
  "similarity": 0.8,
  "reason": "相似度理由"
}
```""",
            
            "inference": """基于以下知识图谱三元组，进行推理以发现新的知识关系：

已知三元组：
{triples}

请推理出可能的新三元组，这些三元组应该基于逻辑推理得出，而不是原文直接表述的。

请以JSON格式返回：
```json
{
  "inferred_triples": [
    {
      "subject": "主语",
      "predicate": "谓语",
      "object": "宾语",
      "confidence": 0.7,
      "reasoning": "推理过程"
    }
  ]
}
```"""
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数（0-1）
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _find_similar_entities(self, entity: str, entity_list: List[str], threshold: float = 0.7) -> List[Tuple[str, float]]:
        """查找相似实体
        
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
        # 简单的实体提取，可以后续优化
        import re
        
        # 提取引号内的内容
        quoted_entities = re.findall(r'["""]([^"""]+)["""]', question)
        
        # 提取可能的关键词（名词）
        # 这里使用简单的规则，实际应用中可以使用更复杂的NLP工具
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
        """查找相关的三元组
        
        Args:
            question: 用户问题
            knowledge_graph: 知识图谱
            
        Returns:
            相关三元组列表
        """
        entities = self._extract_entities_from_question(question)
        relevant_triples = []
        
        # 如果启用了模糊匹配
        if self.config.reasoning.enable_fuzzy_matching:
            all_subjects = list(set(triple.subject for triple in knowledge_graph.triples))
            all_objects = list(set(triple.object for triple in knowledge_graph.triples))
            all_predicates = list(set(triple.predicate for triple in knowledge_graph.triples))
            
            for entity in entities:
                # 查找相似的主语
                similar_subjects = self._find_similar_entities(
                    entity, all_subjects, self.config.reasoning.similarity_threshold
                )
                
                # 查找相似的宾语
                similar_objects = self._find_similar_entities(
                    entity, all_objects, self.config.reasoning.similarity_threshold
                )
                
                # 查找相似的谓语
                similar_predicates = self._find_similar_entities(
                    entity, all_predicates, self.config.reasoning.similarity_threshold
                )
                
                # 收集相关的三元组
                for triple in knowledge_graph.triples:
                    if (any(triple.subject == subj for subj, _ in similar_subjects) or
                        any(triple.object == obj for obj, _ in similar_objects) or
                        any(triple.predicate == pred for pred, _ in similar_predicates)):
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
        
        # 按置信度排序并限制数量
        unique_triples.sort(key=lambda x: x.confidence, reverse=True)
        return unique_triples[:self.config.reasoning.max_triples_per_query]
    
    async def _get_semantic_similarity(self, concept1: str, concept2: str) -> float:
        """获取语义相似度
        
        Args:
            concept1: 概念1
            concept2: 概念2
            
        Returns:
            相似度分数
        """
        try:
            prompt = self.prompts["similarity"].format(
                concept1=concept1,
                concept2=concept2
            )
            
            response = await self.client.chat.completions.create(
                model=self.config.reasoning.reasoning_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的知识推理专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens,
                extra_body={"enable_thinking": False}
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON响应
            try:
                result = json.loads(content)
                return float(result.get("similarity", 0.0))
            except json.JSONDecodeError:
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                    return float(result.get("similarity", 0.0))
                else:
                    self.logger.warning(f"无法解析相似度响应: {content}")
                    return self._calculate_similarity(concept1, concept2)
                    
        except Exception as e:
            self.logger.error(f"获取语义相似度失败: {e}")
            return self._calculate_similarity(concept1, concept2)
    
    async def _perform_reasoning(
        self, 
        question: str, 
        relevant_triples: List[KnowledgeTriple]
    ) -> Dict[str, Any]:
        """执行推理过程
        
        Args:
            question: 用户问题
            relevant_triples: 相关三元组
            
        Returns:
            推理结果
        """
        try:
            # 准备三元组数据
            triples_text = "\n".join([
                f"- {triple.subject} -> {triple.predicate} -> {triple.object} (置信度: {triple.confidence})"
                for triple in relevant_triples
            ])
            
            prompt = self.prompts["query"].format(
                triples=triples_text,
                question=question
            )
            
            response = await self.client.chat.completions.create(
                model=self.config.reasoning.reasoning_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的知识图谱推理专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens,
                extra_body={"enable_thinking": False}
            )
            
            content = response.choices[0].message.content
            self.logger.debug(f"推理响应: {content}")
            
            if not content:
                self.logger.error("推理LLM返回空内容")
                return {
                    "answer": "推理失败：模型返回空响应",
                    "confidence": 0.0,
                    "reasoning_steps": [],
                    "source_triples": [],
                    "additional_info": ""
                }
            
            # 解析JSON响应
            result = {}
            
            # 方法1: 直接解析整个响应
            try:
                result = json.loads(content)
                self.logger.info("推理方法1成功: 直接解析JSON")
            except json.JSONDecodeError as e:
                self.logger.warning(f"推理方法1失败: {e}")
                
                # 方法2: 提取```json代码块
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match and json_match.group(1):
                    try:
                        result = json.loads(json_match.group(1))
                        self.logger.info("推理方法2成功: 提取JSON代码块")
                    except json.JSONDecodeError as e2:
                        self.logger.warning(f"推理方法2失败: {e2}")
                else:
                    self.logger.warning("推理方法2失败: 未找到JSON代码块")
                
                # 方法3: 查找包含"answer"的JSON对象
                if not result:
                    json_match2 = re.search(r'\{[^}]*"answer"[^}]*\}', content, re.DOTALL)
                    if json_match2 and json_match2.group(0):
                        try:
                            result = json.loads(json_match2.group(0))
                            self.logger.info("推理方法3成功: 查找answer对象")
                        except json.JSONDecodeError:
                            self.logger.warning("推理方法3失败: 无法解析answer对象")
                    else:
                        self.logger.warning("推理方法3失败: 未找到answer对象")
                
                # 方法4: 尝试修复常见的JSON格式问题
                if not result:
                    try:
                        # 移除可能的前后缀
                        cleaned_content = content.strip()
                        if cleaned_content.startswith('```json'):
                            cleaned_content = cleaned_content[7:]
                        if cleaned_content.endswith('```'):
                            cleaned_content = cleaned_content[:-3]
                        cleaned_content = cleaned_content.strip()
                        
                        # 尝试解析
                        result = json.loads(cleaned_content)
                        self.logger.info("推理方法4成功: 清理后解析")
                    except json.JSONDecodeError:
                        self.logger.warning("推理方法4失败: 清理后仍无法解析")
                
                # 如果所有方法都失败，返回基本结构
                if not result:
                    self.logger.error(f"推理所有JSON解析方法都失败，原始响应: {repr(content)}")
                    return {
                        "answer": content if content else "推理失败：无法解析响应",
                        "confidence": 0.3,
                        "reasoning_steps": ["JSON解析失败"],
                        "source_triples": [],
                        "additional_info": ""
                    }
            
            return result
                    
        except Exception as e:
            self.logger.error(f"执行推理失败: {e}")
            return {
                "answer": f"推理过程中出现错误: {e}",
                "confidence": 0.0,
                "reasoning_steps": [],
                "source_triples": [],
                "additional_info": ""
            }
    
    async def query(
        self, 
        question: str, 
        knowledge_graph: KnowledgeGraph
    ) -> QueryResult:
        """查询知识图谱并回答问题
        
        Args:
            question: 用户问题
            knowledge_graph: 知识图谱
            
        Returns:
            查询结果
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"开始查询问题: {question}")
            
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
            
            # 执行推理
            reasoning_result = await self._perform_reasoning(question, relevant_triples)
            
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
                    "model": self.config.reasoning.reasoning_model
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
            
            self.logger.info(f"查询完成，置信度: {query_result.confidence}")
            return query_result
            
        except Exception as e:
            error_msg = f"查询失败: {e}"
            self.logger.error(error_msg)
            
            return QueryResult(
                question=question,
                answer=f"查询过程中出现错误: {e}",
                confidence=0.0,
                source_triples=[],
                reasoning_path=["查询失败"],
                metadata={
                    "processing_time": time.time() - start_time,
                    "error": str(e)
                }
            )
    
    async def infer_new_knowledge(self, knowledge_graph: KnowledgeGraph) -> List[KnowledgeTriple]:
        """推理新知识
        
        Args:
            knowledge_graph: 现有知识图谱
            
        Returns:
            推理出的新三元组列表
        """
        try:
            # 准备三元组数据
            triples_text = "\n".join([
                f"- {triple.subject} -> {triple.predicate} -> {triple.object}"
                for triple in knowledge_graph.triples[:50]  # 限制数量避免token过多
            ])
            
            prompt = self.prompts["inference"].format(triples=triples_text)
            
            response = await self.client.chat.completions.create(
                model=self.config.reasoning.reasoning_model,
                messages=[
                    {"role": "system", "content": "你是一个知识推理专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=self.config.openai.max_tokens,
            )
            
            content = response.choices[0].message.content
            
            # 解析推理结果
            try:
                result = json.loads(content)
                inferred_data = result.get("inferred_triples", [])
            except json.JSONDecodeError:
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                    inferred_data = result.get("inferred_triples", [])
                else:
                    self.logger.warning(f"无法解析推理结果: {content}")
                    return []
            
            # 转换为KnowledgeTriple对象
            inferred_triples = []
            for triple_data in inferred_data:
                try:
                    triple = KnowledgeTriple(
                        subject=triple_data["subject"],
                        predicate=triple_data["predicate"],
                        object=triple_data["object"],
                        triple_type=TripleType.ENTITY_RELATION,  # 默认类型
                        confidence=float(triple_data.get("confidence", 0.5)),
                        metadata={
                            "inferred": True,
                            "reasoning": triple_data.get("reasoning", ""),
                            "model": self.config.reasoning.reasoning_model,
                        }
                    )
                    inferred_triples.append(triple)
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"跳过无效的推理三元组: {triple_data}, 错误: {e}")
                    continue
            
            self.logger.info(f"推理出{len(inferred_triples)}个新三元组")
            return inferred_triples
            
        except Exception as e:
            self.logger.error(f"推理新知识失败: {e}")
            return []
    
    def query_sync(self, question: str, knowledge_graph: KnowledgeGraph) -> QueryResult:
        """同步版本的查询方法
        
        Args:
            question: 用户问题
            knowledge_graph: 知识图谱
            
        Returns:
            查询结果
        """
        return asyncio.run(self.query(question, knowledge_graph))
    
    def infer_new_knowledge_sync(self, knowledge_graph: KnowledgeGraph) -> List[KnowledgeTriple]:
        """同步版本的知识推理方法
        
        Args:
            knowledge_graph: 现有知识图谱
            
        Returns:
            推理出的新三元组列表
        """
        return asyncio.run(self.infer_new_knowledge(knowledge_graph))
    
    def get_graph_statistics(self, knowledge_graph: KnowledgeGraph) -> Dict[str, Any]:
        """获取知识图谱统计信息
        
        Args:
            knowledge_graph: 知识图谱
            
        Returns:
            统计信息
        """
        stats = knowledge_graph.get_statistics()
        
        # 添加额外的统计信息
        subjects = knowledge_graph.get_subjects()
        objects = knowledge_graph.get_objects()
        predicates = knowledge_graph.get_predicates()
        
        # 计算连通性
        all_entities = set(subjects + objects)
        connected_entities = set()
        
        for triple in knowledge_graph.triples:
            connected_entities.add(triple.subject)
            connected_entities.add(triple.object)
        
        stats.update({
            "total_entities": len(all_entities),
            "connected_entities": len(connected_entities),
            "connectivity_ratio": len(connected_entities) / len(all_entities) if all_entities else 0,
            "avg_triples_per_entity": len(knowledge_graph.triples) / len(all_entities) if all_entities else 0,
            "most_common_predicates": self._get_most_common_items(predicates, 5),
            "most_common_subjects": self._get_most_common_items(subjects, 5),
            "most_common_objects": self._get_most_common_items(objects, 5),
        })
        
        return stats
    
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
