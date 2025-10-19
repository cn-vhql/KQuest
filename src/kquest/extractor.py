"""知识抽取器模块"""

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json

import openai
from openai import AsyncOpenAI

from .config import get_config
from .models import (
    DocumentChunk,
    ExtractionResult,
    KnowledgeGraph,
    KnowledgeTriple,
    TripleType,
    TaskStatus,
    ProcessingStatus,
)


class KnowledgeExtractor:
    """知识抽取器"""
    
    def __init__(self, config=None):
        """初始化知识抽取器
        
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
            "extraction": """你是一个专业的知识图谱三元组抽取专家。请从给定的文本中抽取高质量的知识图谱三元组。

抽取规则：
1. 只抽取明确、客观的事实信息
2. 三元组格式：(主语, 谓语/关系, 宾语)
3. 主语和宾语应该是具体的实体、概念或属性值
4. 谓语应该是明确的关系或属性
5. 避免抽取主观意见、模糊表述或不确定性信息
6. 为每个三元组评估置信度（0.0-1.0）

三元组类型：
- entity_relation: 实体间关系 (如: "北京", "是...的首都", "中国")
- entity_attribute: 实体属性 (如: "北京", "人口", "2189万")
- class_relation: 类关系 (如: "狗", "属于", "哺乳动物")
- instance_of: 实例关系 (如: "哈士奇", "是", "狗")

请以JSON格式返回结果：
```json
{{
  "triples": [
    {{
      "subject": "主语",
      "predicate": "谓语/关系", 
      "object": "宾语",
      "triple_type": "entity_relation|entity_attribute|class_relation|instance_of",
      "confidence": 0.9,
      "explanation": "简要说明抽取理由"
    }}
  ]
}}
```

文本内容：
{text}

请开始抽取：""",
            
            "filtering": """请评估以下知识三元组的质量，过滤掉低质量或错误的三元组。

评估标准：
1. 事实准确性：信息是否真实可靠
2. 明确性：表述是否清晰明确
3. 完整性：三元组是否完整
4. 相关性：是否与主题相关
5. 置信度：置信度是否合理

请返回过滤后的三元组列表，移除置信度低于{min_confidence}的三元组：

{triples}

请以JSON格式返回结果：
```json
{
  "filtered_triples": [
    {
      "subject": "主语",
      "predicate": "谓语",
      "object": "宾语", 
      "triple_type": "类型",
      "confidence": 0.8,
      "explanation": "保留理由"
    }
  ],
  "removed_triples": [
    {
      "subject": "主语",
      "predicate": "谓语",
      "object": "宾语",
      "reason": "移除理由"
    }
  ]
}
```"""
        }
    
    def _chunk_text(self, text: str) -> List[DocumentChunk]:
        """将文本分块
        
        Args:
            text: 输入文本
            
        Returns:
            文档块列表
        """
        chunk_size = self.config.extraction.chunk_size
        chunk_overlap = self.config.extraction.chunk_overlap
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 寻找最近的句号、感叹号或问号
                sentence_end = max(
                    text.rfind('。', start, end),
                    text.rfind('！', start, end),
                    text.rfind('？', start, end),
                    text.rfind('.', start, end),
                    text.rfind('!', start, end),
                    text.rfind('?', start, end),
                )
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk = DocumentChunk(
                    content=chunk_text,
                    chunk_id=f"chunk_{len(chunks)}",
                    source_file="",  # 将在调用时设置
                    start_position=start,
                    end_position=end,
                )
                chunks.append(chunk)
            
            # 计算下一个块的起始位置（考虑重叠）
            start = max(start + 1, end - chunk_overlap)
        
        return chunks
    
    async def _extract_from_chunk(self, chunk: DocumentChunk) -> List[KnowledgeTriple]:
        """从单个文档块中抽取三元组
        
        Args:
            chunk: 文档块
            
        Returns:
            抽取的三元组列表
        """
        try:
            prompt = self.prompts["extraction"].format(text=chunk.content.replace('{', '{{').replace('}', '}}'))
            
            response = await self.client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的知识图谱抽取专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens,
                extra_body={"enable_thinking": False}
            )
            
            content = response.choices[0].message.content
            self.logger.debug(f"LLM响应: {content}")
            
            if not content:
                self.logger.error("LLM返回空内容")
                return []
            
            # 解析JSON响应
            triples_data = []
            
            # 方法1: 直接解析整个响应
            try:
                result = json.loads(content)
                triples_data = result.get("triples", [])
                self.logger.info("方法1成功: 直接解析JSON")
            except json.JSONDecodeError as e:
                self.logger.warning(f"方法1失败: {e}")
                
                # 方法2: 提取```json代码块
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match and json_match.group(1):
                    try:
                        result = json.loads(json_match.group(1))
                        triples_data = result.get("triples", [])
                        self.logger.info("方法2成功: 提取JSON代码块")
                    except json.JSONDecodeError as e2:
                        self.logger.warning(f"方法2失败: {e2}")
                else:
                    self.logger.warning("方法2失败: 未找到JSON代码块")
                
                # 方法3: 查找包含"triples"的JSON对象
                if not triples_data:
                    json_match2 = re.search(r'\{[^}]*"triples"[^}]*\}', content, re.DOTALL)
                    if json_match2 and json_match2.group(0):
                        try:
                            result = json.loads(json_match2.group(0))
                            triples_data = result.get("triples", [])
                            self.logger.info("方法3成功: 查找triples对象")
                        except json.JSONDecodeError:
                            self.logger.warning("方法3失败: 无法解析triples对象")
                    else:
                        self.logger.warning("方法3失败: 未找到triples对象")
                
                # 方法4: 尝试修复常见的JSON格式问题
                if not triples_data:
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
                        triples_data = result.get("triples", [])
                        self.logger.info("方法4成功: 清理后解析")
                    except json.JSONDecodeError:
                        self.logger.warning("方法4失败: 清理后仍无法解析")
                
                # 如果所有方法都失败，记录完整响应用于调试
                if not triples_data:
                    self.logger.error(f"所有JSON解析方法都失败，原始响应: {repr(content)}")
                    return []
            
            # 转换为KnowledgeTriple对象
            triples = []
            for triple_data in triples_data:
                try:
                    triple = KnowledgeTriple(
                        subject=triple_data["subject"],
                        predicate=triple_data["predicate"],
                        object=triple_data["object"],
                        triple_type=TripleType(triple_data["triple_type"]),
                        confidence=float(triple_data.get("confidence", 0.5)),
                        source=chunk.content,
                        metadata={
                            "chunk_id": chunk.chunk_id,
                            "explanation": triple_data.get("explanation", ""),
                            "model": self.config.openai.model,
                        }
                    )
                    triples.append(triple)
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"跳过无效的三元组数据: {triple_data}, 错误: {e}")
                    continue
            
            return triples
            
        except Exception as e:
            self.logger.error(f"从文档块抽取三元组失败: {e}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
            return []
    
    async def _filter_triples(self, triples: List[KnowledgeTriple]) -> List[KnowledgeTriple]:
        """过滤三元组
        
        Args:
            triples: 原始三元组列表
            
        Returns:
            过滤后的三元组列表
        """
        if not self.config.extraction.enable_filtering:
            return triples
        
        try:
            # 准备三元组数据
            triples_data = []
            for triple in triples:
                triples_data.append({
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object,
                    "triple_type": triple.triple_type.value,
                    "confidence": triple.confidence,
                })
            
            prompt = self.prompts["filtering"].format(
                triples=json.dumps(triples_data, ensure_ascii=False, indent=2),
                min_confidence=self.config.extraction.min_confidence
            )
            
            response = await self.client.chat.completions.create(
                model=self.config.openai.model,
                messages=[
                    {"role": "system", "content": "你是一个知识图谱质量控制专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.openai.temperature,
                max_tokens=self.config.openai.max_tokens,
            )
            
            content = response.choices[0].message.content
            
            if not content:
                self.logger.error("过滤LLM返回空内容")
                return triples
            
            # 解析过滤结果
            try:
                result = json.loads(content)
                filtered_data = result.get("filtered_triples", [])
            except json.JSONDecodeError as e:
                self.logger.error(f"过滤结果JSON解析失败: {e}, 原始内容: {content}")
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match and json_match.group(1):
                    try:
                        result = json.loads(json_match.group(1))
                        filtered_data = result.get("filtered_triples", [])
                    except json.JSONDecodeError as e2:
                        self.logger.error(f"提取的过滤JSON也解析失败: {e2}")
                        return triples
                else:
                    # 尝试查找任何JSON格式的数据
                    json_match2 = re.search(r'\{.*"filtered_triples".*\}', content, re.DOTALL)
                    if json_match2 and json_match2.group(0):
                        try:
                            result = json.loads(json_match2.group(0))
                            filtered_data = result.get("filtered_triples", [])
                        except json.JSONDecodeError:
                            self.logger.warning(f"无法解析过滤结果: {content}")
                            return triples
                    else:
                        self.logger.warning(f"无法解析过滤结果: {content}")
                        return triples
            
            # 重建过滤后的三元组列表
            filtered_triples = []
            for filtered_item in filtered_data:
                # 查找对应的三元组
                for triple in triples:
                    if (triple.subject == filtered_item["subject"] and
                        triple.predicate == filtered_item["predicate"] and
                        triple.object == filtered_item["object"]):
                        # 更新置信度和元数据
                        triple.confidence = float(filtered_item.get("confidence", triple.confidence))
                        triple.metadata["filtering_explanation"] = filtered_item.get("explanation", "")
                        filtered_triples.append(triple)
                        break
            
            return filtered_triples
            
        except Exception as e:
            self.logger.error(f"过滤三元组失败: {e}")
            return triples
    
    async def extract_from_text(
        self, 
        text: str, 
        source_file: str = "",
        task_status: Optional[TaskStatus] = None
    ) -> ExtractionResult:
        """从文本中抽取知识图谱
        
        Args:
            text: 输入文本
            source_file: 源文件路径
            task_status: 任务状态对象（用于进度更新）
            
        Returns:
            抽取结果
        """
        start_time = time.time()
        
        try:
            if task_status:
                task_status.update_progress(0.1, "开始文本分块")
            
            # 文本分块
            chunks = self._chunk_text(text)
            
            # 设置源文件信息
            for chunk in chunks:
                chunk.source_file = source_file
            
            if task_status:
                task_status.update_progress(0.2, f"文本分为{len(chunks)}个块")
            
            self.logger.info(f"文本分块完成，共{len(chunks)}个块")
            
            # 批量处理文档块
            all_triples = []
            max_chunks_per_request = self.config.extraction.max_chunks_per_request
            
            for i in range(0, len(chunks), max_chunks_per_request):
                batch_chunks = chunks[i:i + max_chunks_per_request]
                
                if task_status:
                    progress = 0.2 + (i / len(chunks)) * 0.6
                    task_status.update_progress(progress, f"处理第{i//max_chunks_per_request + 1}批文档块")
                
                # 并发处理当前批次
                batch_tasks = [self._extract_from_chunk(chunk) for chunk in batch_chunks]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # 合并结果
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        self.logger.error(f"处理文档块{batch_chunks[j].chunk_id}失败: {result}")
                    elif isinstance(result, list):
                        all_triples.extend(result)
                
                # 添加延迟以避免API限制
                if i + max_chunks_per_request < len(chunks):
                    await asyncio.sleep(self.config.openai.retry_delay)
            
            if task_status:
                task_status.update_progress(0.8, "过滤三元组")
            
            # 过滤三元组
            filtered_triples = await self._filter_triples(all_triples)
            
            if task_status:
                task_status.update_progress(0.9, "构建知识图谱")
            
            # 构建知识图谱
            knowledge_graph = KnowledgeGraph(
                triples=filtered_triples,
                metadata={
                    "source_file": source_file,
                    "extraction_model": self.config.openai.model,
                    "total_chunks": len(chunks),
                    "raw_triples": len(all_triples),
                    "filtered_triples": len(filtered_triples),
                    "config": self.config.extraction.dict(),
                }
            )
            
            processing_time = time.time() - start_time
            
            result = ExtractionResult(
                knowledge_graph=knowledge_graph,
                source_file=source_file,
                processing_time=processing_time,
                total_characters=len(text),
                extracted_triples=len(filtered_triples),
                success=True,
                metadata={
                    "chunks_count": len(chunks),
                    "raw_triples_count": len(all_triples),
                    "model": self.config.openai.model,
                }
            )
            
            if task_status:
                task_status.set_completed(result)
            
            self.logger.info(f"知识抽取完成，耗时{processing_time:.2f}秒，抽取{len(filtered_triples)}个三元组")
            
            return result
            
        except Exception as e:
            error_msg = f"知识抽取失败: {e}"
            self.logger.error(error_msg)
            
            processing_time = time.time() - start_time
            
            result = ExtractionResult(
                knowledge_graph=KnowledgeGraph(),
                source_file=source_file,
                processing_time=processing_time,
                total_characters=len(text),
                extracted_triples=0,
                success=False,
                error_message=error_msg
            )
            
            if task_status:
                task_status.set_failed(error_msg)
            
            return result
    
    async def extract_from_file(
        self, 
        file_path: Union[str, Path],
        task_status: Optional[TaskStatus] = None
    ) -> ExtractionResult:
        """从文件中抽取知识图谱
        
        Args:
            file_path: 文件路径
            task_status: 任务状态对象
            
        Returns:
            抽取结果
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            error_msg = f"文件不存在: {file_path}"
            self.logger.error(error_msg)
            if task_status:
                task_status.set_failed(error_msg)
            return ExtractionResult(
                knowledge_graph=KnowledgeGraph(),
                source_file=str(file_path),
                processing_time=0.0,
                total_characters=0,
                extracted_triples=0,
                success=False,
                error_message=error_msg
            )
        
        try:
            if task_status:
                task_status.update_progress(0.05, f"读取文件: {file_path.name}")
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.logger.info(f"成功读取文件: {file_path}, 大小: {len(content)}字符")
            
            # 从文本抽取
            return await self.extract_from_text(
                text=content,
                source_file=str(file_path),
                task_status=task_status
            )
            
        except Exception as e:
            error_msg = f"读取文件失败: {e}"
            self.logger.error(error_msg)
            if task_status:
                task_status.set_failed(error_msg)
            return ExtractionResult(
                knowledge_graph=KnowledgeGraph(),
                source_file=str(file_path),
                processing_time=0.0,
                total_characters=0,
                extracted_triples=0,
                success=False,
                error_message=error_msg
            )
    
    def extract_from_text_sync(self, text: str, source_file: str = "") -> ExtractionResult:
        """同步版本的文本抽取方法
        
        Args:
            text: 输入文本
            source_file: 源文件路径
            
        Returns:
            抽取结果
        """
        return asyncio.run(self.extract_from_text(text, source_file))
    
    def extract_from_file_sync(self, file_path: Union[str, Path]) -> ExtractionResult:
        """同步版本的文件抽取方法
        
        Args:
            file_path: 文件路径
            
        Returns:
            抽取结果
        """
        return asyncio.run(self.extract_from_file(file_path))
