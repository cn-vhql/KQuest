"""数据模型定义"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class TripleType(str, Enum):
    """三元组类型枚举"""
    ENTITY_RELATION = "entity_relation"  # 实体关系
    ENTITY_ATTRIBUTE = "entity_attribute"  # 实体属性
    CLASS_RELATION = "class_relation"  # 类关系
    INSTANCE_OF = "instance_of"  # 实例关系


class ConfidenceLevel(str, Enum):
    """置信度级别"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeTriple(BaseModel):
    """知识三元组模型"""
    subject: str = Field(..., description="主语")
    predicate: str = Field(..., description="谓语/关系")
    object: str = Field(..., description="宾语")
    triple_type: TripleType = Field(..., description="三元组类型")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="置信度级别")
    source: Optional[str] = Field(default=None, description="来源文本")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    @validator('confidence_level', pre=True, always=True)
    def set_confidence_level(cls, v, values):
        """根据置信度自动设置置信度级别"""
        if 'confidence' in values:
            confidence = values['confidence']
            if confidence >= 0.8:
                return ConfidenceLevel.HIGH
            elif confidence >= 0.5:
                return ConfidenceLevel.MEDIUM
            else:
                return ConfidenceLevel.LOW
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def __str__(self) -> str:
        return f"{self.subject} --{self.predicate}--> {self.object}"
    
    def to_rdf_tuple(self) -> tuple:
        """转换为RDF三元组格式"""
        return (self.subject, self.predicate, self.object)


class KnowledgeGraph(BaseModel):
    """知识图谱模型"""
    triples: List[KnowledgeTriple] = Field(default_factory=list, description="三元组列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="图谱元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    def add_triple(self, triple: KnowledgeTriple) -> None:
        """添加三元组"""
        self.triples.append(triple)
        self.updated_at = datetime.now()
    
    def remove_triple(self, index: int) -> bool:
        """删除指定索引的三元组"""
        if 0 <= index < len(self.triples):
            self.triples.pop(index)
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_subjects(self) -> List[str]:
        """获取所有主语"""
        return list(set(triple.subject for triple in self.triples))
    
    def get_objects(self) -> List[str]:
        """获取所有宾语"""
        return list(set(triple.object for triple in self.triples))
    
    def get_predicates(self) -> List[str]:
        """获取所有谓语"""
        return list(set(triple.predicate for triple in self.triples))
    
    def find_triples_by_subject(self, subject: str) -> List[KnowledgeTriple]:
        """根据主语查找三元组"""
        return [triple for triple in self.triples if triple.subject == subject]
    
    def find_triples_by_object(self, object: str) -> List[KnowledgeTriple]:
        """根据宾语查找三元组"""
        return [triple for triple in self.triples if triple.object == object]
    
    def find_triples_by_predicate(self, predicate: str) -> List[KnowledgeTriple]:
        """根据谓语查找三元组"""
        return [triple for triple in self.triples if triple.predicate == predicate]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return {
            "total_triples": len(self.triples),
            "unique_subjects": len(self.get_subjects()),
            "unique_objects": len(self.get_objects()),
            "unique_predicates": len(self.get_predicates()),
            "triple_types": {
                triple_type.value: len([t for t in self.triples if t.triple_type == triple_type])
                for triple_type in TripleType
            },
            "confidence_distribution": {
                level.value: len([t for t in self.triples if t.confidence_level == level])
                for level in ConfidenceLevel
            }
        }


class QueryResult(BaseModel):
    """查询结果模型"""
    question: str = Field(..., description="查询问题")
    answer: str = Field(..., description="回答")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="回答置信度")
    source_triples: List[KnowledgeTriple] = Field(default_factory=list, description="来源三元组")
    reasoning_path: List[str] = Field(default_factory=list, description="推理路径")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    def add_source_triple(self, triple: KnowledgeTriple) -> None:
        """添加来源三元组"""
        if triple not in self.source_triples:
            self.source_triples.append(triple)
    
    def add_reasoning_step(self, step: str) -> None:
        """添加推理步骤"""
        self.reasoning_path.append(step)


class ExtractionResult(BaseModel):
    """抽取结果模型"""
    knowledge_graph: KnowledgeGraph = Field(..., description="抽取的知识图谱")
    source_file: str = Field(..., description="源文件路径")
    processing_time: float = Field(..., description="处理时间（秒）")
    total_characters: int = Field(..., description="总字符数")
    extracted_triples: int = Field(..., description="抽取的三元组数量")
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class DocumentChunk(BaseModel):
    """文档块模型"""
    content: str = Field(..., description="文档内容")
    chunk_id: str = Field(..., description="块ID")
    source_file: str = Field(..., description="源文件")
    start_position: int = Field(..., description="开始位置")
    end_position: int = Field(..., description="结束位置")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    def length(self) -> int:
        """获取内容长度"""
        return len(self.content)


class ProcessingStatus(str, Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str = Field(..., description="任务ID")
    status: ProcessingStatus = Field(..., description="处理状态")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="进度")
    message: str = Field(default="", description="状态消息")
    result: Optional[ExtractionResult] = Field(default=None, description="处理结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    def update_progress(self, progress: float, message: str = "") -> None:
        """更新进度"""
        self.progress = max(0.0, min(1.0, progress))
        if message:
            self.message = message
        self.updated_at = datetime.now()
    
    def set_completed(self, result: ExtractionResult) -> None:
        """设置为完成状态"""
        self.status = ProcessingStatus.COMPLETED
        self.progress = 1.0
        self.result = result
        self.message = "处理完成"
        self.updated_at = datetime.now()
    
    def set_failed(self, error: str) -> None:
        """设置为失败状态"""
        self.status = ProcessingStatus.FAILED
        self.error = error
        self.message = f"处理失败: {error}"
        self.updated_at = datetime.now()
