"""存储管理模块"""

import json
import logging
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import rdflib
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

from .config import get_config
from .models import KnowledgeGraph, KnowledgeTriple, TripleType


class KnowledgeStorage:
    """知识图谱存储管理器"""
    
    def __init__(self, config=None):
        """初始化存储管理器
        
        Args:
            config: 配置对象，如果为None则使用全局配置
        """
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        Path(self.config.storage.output_dir).mkdir(parents=True, exist_ok=True)
    
    def save_knowledge_graph(
        self, 
        knowledge_graph: KnowledgeGraph, 
        file_path: Union[str, Path],
        format: Optional[str] = None,
        compress: Optional[bool] = None
    ) -> bool:
        """保存知识图谱到文件
        
        Args:
            knowledge_graph: 知识图谱对象
            file_path: 输出文件路径
            format: 文件格式，如果为None则使用配置中的默认格式
            compress: 是否压缩，如果为None则使用配置中的默认设置
            
        Returns:
            是否保存成功
        """
        try:
            file_path = Path(file_path)
            format = format or self.config.storage.default_format
            compress = compress if compress is not None else self.config.storage.compression
            
            # 如果启用了备份，先备份现有文件
            if self.config.storage.backup_enabled and file_path.exists():
                self._backup_file(file_path)
            
            # 根据格式选择保存方法
            if format == "rdf":
                success = self._save_as_rdf(knowledge_graph, file_path)
            elif format == "json":
                success = self._save_as_json(knowledge_graph, file_path)
            elif format == "jsonld":
                success = self._save_as_jsonld(knowledge_graph, file_path)
            elif format == "csv":
                success = self._save_as_csv(knowledge_graph, file_path)
            elif format == "ttl":
                success = self._save_as_turtle(knowledge_graph, file_path)
            else:
                raise ValueError(f"不支持的格式: {format}")
            
            if success and compress:
                self._compress_file(file_path)
            
            self.logger.info(f"知识图谱已保存到: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存知识图谱失败: {e}")
            return False
    
    def load_knowledge_graph(self, file_path: Union[str, Path]) -> Optional[KnowledgeGraph]:
        """从文件加载知识图谱
        
        Args:
            file_path: 文件路径
            
        Returns:
            知识图谱对象，如果加载失败则返回None
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.error(f"文件不存在: {file_path}")
                return None
            
            # 检查是否是压缩文件
            if file_path.suffix == '.gz':
                file_path = self._decompress_file(file_path)
            
            # 根据文件扩展名确定格式
            format = self._detect_format(file_path)
            
            # 根据格式选择加载方法
            if format == "rdf":
                knowledge_graph = self._load_from_rdf(file_path)
            elif format == "json":
                knowledge_graph = self._load_from_json(file_path)
            elif format == "jsonld":
                knowledge_graph = self._load_from_jsonld(file_path)
            elif format == "csv":
                knowledge_graph = self._load_from_csv(file_path)
            elif format == "ttl":
                knowledge_graph = self._load_from_turtle(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {format}")
            
            self.logger.info(f"知识图谱已从文件加载: {file_path}")
            return knowledge_graph
            
        except Exception as e:
            self.logger.error(f"加载知识图谱失败: {e}")
            return None
    
    def _save_as_rdf(self, knowledge_graph: KnowledgeGraph, file_path: Path) -> bool:
        """保存为RDF/XML格式"""
        try:
            graph = Graph()
            
            # 创建命名空间
            kq = Namespace("http://kquest.org/knowledge/")
            graph.bind("kq", kq)
            
            # 添加三元组到RDF图
            for triple in knowledge_graph.triples:
                subject_uri = URIRef(f"{kq}{self._sanitize_uri(triple.subject)}")
                predicate_uri = URIRef(f"{kq}{self._sanitize_uri(triple.predicate)}")
                
                # 根据三元组类型确定宾语类型
                if triple.triple_type == TripleType.ENTITY_ATTRIBUTE:
                    # 属性值使用字面量
                    object_literal = Literal(triple.object, datatype=XSD.string)
                    graph.add((subject_uri, predicate_uri, object_literal))
                else:
                    # 实体关系使用URI
                    object_uri = URIRef(f"{kq}{self._sanitize_uri(triple.object)}")
                    graph.add((subject_uri, predicate_uri, object_uri))
                
                # 添加元数据
                graph.add((subject_uri, RDFS.comment, Literal(triple.source or "")))
                graph.add((subject_uri, kq.confidence, Literal(triple.confidence)))
                graph.add((subject_uri, kq.tripleType, Literal(triple.triple_type.value)))
            
            # 保存图谱元数据
            graph_uri = URIRef(f"{kq}graph_{datetime.now().isoformat()}")
            graph.add((graph_uri, RDF.type, kq.KnowledgeGraph))
            graph.add((graph_uri, kq.tripleCount, Literal(len(knowledge_graph.triples))))
            graph.add((graph_uri, kq.createdAt, Literal(knowledge_graph.created_at.isoformat())))
            
            # 序列化到文件
            graph.serialize(destination=str(file_path), format='xml')
            return True
            
        except Exception as e:
            self.logger.error(f"保存RDF格式失败: {e}")
            return False
    
    def _save_as_json(self, knowledge_graph: KnowledgeGraph, file_path: Path) -> bool:
        """保存为JSON格式"""
        try:
            data = {
                "metadata": {
                    "created_at": knowledge_graph.created_at.isoformat(),
                    "updated_at": knowledge_graph.updated_at.isoformat(),
                    "total_triples": len(knowledge_graph.triples),
                    **knowledge_graph.metadata
                },
                "triples": []
            }
            
            for triple in knowledge_graph.triples:
                triple_data = {
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object,
                    "triple_type": triple.triple_type.value,
                    "confidence": triple.confidence,
                    "confidence_level": triple.confidence_level.value,
                    "source": triple.source,
                    "created_at": triple.created_at.isoformat(),
                    "metadata": triple.metadata
                }
                data["triples"].append(triple_data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存JSON格式失败: {e}")
            return False
    
    def _save_as_jsonld(self, knowledge_graph: KnowledgeGraph, file_path: Path) -> bool:
        """保存为JSON-LD格式"""
        try:
            # JSON-LD上下文
            context = {
                "@context": {
                    "kq": "http://kquest.org/knowledge/",
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "xsd": "http://www.w3.org/2001/XMLSchema#",
                    "subject": {"@id": "rdf:subject"},
                    "predicate": {"@id": "rdf:predicate"},
                    "object": {"@id": "rdf:object"},
                    "confidence": {"@id": "kq:confidence", "@type": "xsd:decimal"},
                    "tripleType": {"@id": "kq:tripleType"},
                    "createdAt": {"@id": "kq:createdAt", "@type": "xsd:dateTime"}
                }
            }
            
            # 转换三元组
            triples = []
            for triple in knowledge_graph.triples:
                triple_data = {
                    "@id": f"kq:{self._sanitize_uri(triple.subject)}",
                    "kq:hasRelation": {
                        "@id": f"kq:{self._sanitize_uri(triple.predicate)}",
                        "rdf:object": f"kq:{self._sanitize_uri(triple.object)}",
                        "kq:confidence": triple.confidence,
                        "kq:tripleType": triple.triple_type.value
                    }
                }
                triples.append(triple_data)
            
            # 构建完整文档
            document = {
                **context,
                "@graph": triples,
                "kq:KnowledgeGraph": {
                    "kq:tripleCount": len(knowledge_graph.triples),
                    "kq:createdAt": knowledge_graph.created_at.isoformat()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存JSON-LD格式失败: {e}")
            return False
    
    def _save_as_csv(self, knowledge_graph: KnowledgeGraph, file_path: Path) -> bool:
        """保存为CSV格式"""
        try:
            import csv
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入表头
                writer.writerow([
                    'subject', 'predicate', 'object', 'triple_type',
                    'confidence', 'confidence_level', 'source', 'created_at'
                ])
                
                # 写入数据
                for triple in knowledge_graph.triples:
                    writer.writerow([
                        triple.subject,
                        triple.predicate,
                        triple.object,
                        triple.triple_type.value,
                        triple.confidence,
                        triple.confidence_level.value,
                        triple.source or '',
                        triple.created_at.isoformat()
                    ])
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存CSV格式失败: {e}")
            return False
    
    def _save_as_turtle(self, knowledge_graph: KnowledgeGraph, file_path: Path) -> bool:
        """保存为Turtle格式"""
        try:
            graph = Graph()
            
            # 创建命名空间
            kq = Namespace("http://kquest.org/knowledge/")
            graph.bind("kq", kq)
            graph.bind("rdf", RDF)
            graph.bind("rdfs", RDFS)
            
            # 添加三元组
            for triple in knowledge_graph.triples:
                subject_uri = URIRef(f"{kq}{self._sanitize_uri(triple.subject)}")
                predicate_uri = URIRef(f"{kq}{self._sanitize_uri(triple.predicate)}")
                
                if triple.triple_type == TripleType.ENTITY_ATTRIBUTE:
                    object_literal = Literal(triple.object)
                    graph.add((subject_uri, predicate_uri, object_literal))
                else:
                    object_uri = URIRef(f"{kq}{self._sanitize_uri(triple.object)}")
                    graph.add((subject_uri, predicate_uri, object_uri))
            
            # 序列化为Turtle格式
            graph.serialize(destination=str(file_path), format='turtle')
            return True
            
        except Exception as e:
            self.logger.error(f"保存Turtle格式失败: {e}")
            return False
    
    def _load_from_rdf(self, file_path: Path) -> KnowledgeGraph:
        """从RDF/XML格式加载"""
        try:
            graph = Graph()
            graph.parse(str(file_path), format='xml')
            
            triples = []
            for s, p, o in graph:
                # 跳过元数据三元组
                if str(p).endswith('confidence') or str(p).endswith('tripleType'):
                    continue
                
                # 获取置信度
                confidence_query = graph.value(s, URIRef("http://kquest.org/knowledge/confidence"))
                confidence = float(confidence_query) if confidence_query else 1.0
                
                # 获取三元组类型
                type_query = graph.value(s, URIRef("http://kquest.org/knowledge/tripleType"))
                triple_type = TripleType(str(type_query)) if type_query else TripleType.ENTITY_RELATION
                
                triple = KnowledgeTriple(
                    subject=str(s).replace("http://kquest.org/knowledge/", ""),
                    predicate=str(p).replace("http://kquest.org/knowledge/", ""),
                    object=str(o).replace("http://kquest.org/knowledge/", ""),
                    triple_type=triple_type,
                    confidence=confidence
                )
                triples.append(triple)
            
            return KnowledgeGraph(triples=triples)
            
        except Exception as e:
            self.logger.error(f"加载RDF格式失败: {e}")
            raise
    
    def _load_from_json(self, file_path: Path) -> KnowledgeGraph:
        """从JSON格式加载"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            triples = []
            for triple_data in data.get("triples", []):
                triple = KnowledgeTriple(
                    subject=triple_data["subject"],
                    predicate=triple_data["predicate"],
                    object=triple_data["object"],
                    triple_type=TripleType(triple_data["triple_type"]),
                    confidence=triple_data.get("confidence", 1.0),
                    source=triple_data.get("source"),
                    metadata=triple_data.get("metadata", {})
                )
                triples.append(triple)
            
            knowledge_graph = KnowledgeGraph(
                triples=triples,
                metadata=data.get("metadata", {})
            )
            
            # 恢复时间戳
            if "created_at" in data.get("metadata", {}):
                knowledge_graph.created_at = datetime.fromisoformat(data["metadata"]["created_at"])
            if "updated_at" in data.get("metadata", {}):
                knowledge_graph.updated_at = datetime.fromisoformat(data["metadata"]["updated_at"])
            
            return knowledge_graph
            
        except Exception as e:
            self.logger.error(f"加载JSON格式失败: {e}")
            raise
    
    def _load_from_jsonld(self, file_path: Path) -> KnowledgeGraph:
        """从JSON-LD格式加载"""
        # 简化实现，实际应该完整解析JSON-LD
        return self._load_from_json(file_path)
    
    def _load_from_csv(self, file_path: Path) -> KnowledgeGraph:
        """从CSV格式加载"""
        try:
            import csv
            
            triples = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    triple = KnowledgeTriple(
                        subject=row['subject'],
                        predicate=row['predicate'],
                        object=row['object'],
                        triple_type=TripleType(row['triple_type']),
                        confidence=float(row.get('confidence', 1.0)),
                        source=row.get('source', '')
                    )
                    triples.append(triple)
            
            return KnowledgeGraph(triples=triples)
            
        except Exception as e:
            self.logger.error(f"加载CSV格式失败: {e}")
            raise
    
    def _load_from_turtle(self, file_path: Path) -> KnowledgeGraph:
        """从Turtle格式加载"""
        try:
            graph = Graph()
            graph.parse(str(file_path), format='turtle')
            
            triples = []
            for s, p, o in graph:
                triple = KnowledgeTriple(
                    subject=str(s).replace("http://kquest.org/knowledge/", ""),
                    predicate=str(p).replace("http://kquest.org/knowledge/", ""),
                    object=str(o).replace("http://kquest.org/knowledge/", ""),
                    triple_type=TripleType.ENTITY_RELATION
                )
                triples.append(triple)
            
            return KnowledgeGraph(triples=triples)
            
        except Exception as e:
            self.logger.error(f"加载Turtle格式失败: {e}")
            raise
    
    def _detect_format(self, file_path: Path) -> str:
        """检测文件格式"""
        suffix = file_path.suffix.lower()
        
        format_map = {
            '.rdf': 'rdf',
            '.xml': 'rdf',
            '.json': 'json',
            '.jsonld': 'jsonld',
            '.csv': 'csv',
            '.ttl': 'turtle',
            '.n3': 'turtle'
        }
        
        return format_map.get(suffix, 'json')
    
    def _sanitize_uri(self, text: str) -> str:
        """清理文本以用作URI"""
        # 移除或替换不安全的字符
        import re
        sanitized = re.sub(r'[^\w\-_\.]', '_', text)
        return sanitized
    
    def _backup_file(self, file_path: Path) -> None:
        """备份文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f".{timestamp}{file_path.suffix}")
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"文件已备份到: {backup_path}")
        except Exception as e:
            self.logger.warning(f"备份文件失败: {e}")
    
    def _compress_file(self, file_path: Path) -> None:
        """压缩文件"""
        try:
            compressed_path = file_path.with_suffix(f"{file_path.suffix}.gz")
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除原文件
            file_path.unlink()
            self.logger.info(f"文件已压缩到: {compressed_path}")
        except Exception as e:
            self.logger.error(f"压缩文件失败: {e}")
    
    def _decompress_file(self, file_path: Path) -> Path:
        """解压缩文件"""
        try:
            decompressed_path = file_path.with_suffix('')
            with gzip.open(file_path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return decompressed_path
        except Exception as e:
            self.logger.error(f"解压缩文件失败: {e}")
            raise
    
    def list_saved_graphs(self, directory: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """列出已保存的知识图谱文件
        
        Args:
            directory: 目录路径，如果为None则使用配置中的输出目录
            
        Returns:
            文件信息列表
        """
        try:
            directory = Path(directory or self.config.storage.output_dir)
            
            if not directory.exists():
                return []
            
            files = []
            for file_path in directory.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    stat = file_path.stat()
                    
                    # 尝试加载文件获取基本信息
                    try:
                        kg = self.load_knowledge_graph(file_path)
                        if kg:
                            files.append({
                                "path": str(file_path),
                                "name": file_path.name,
                                "format": self._detect_format(file_path),
                                "size": stat.st_size,
                                "created_at": datetime.fromtimestamp(stat.st_ctime),
                                "modified_at": datetime.fromtimestamp(stat.st_mtime),
                                "triples_count": len(kg.triples),
                                "subjects_count": len(kg.get_subjects()),
                                "objects_count": len(kg.get_objects())
                            })
                    except Exception:
                        # 如果无法加载，仍然包含基本信息
                        files.append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "format": self._detect_format(file_path),
                            "size": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_ctime),
                            "modified_at": datetime.fromtimestamp(stat.st_mtime),
                            "error": "无法加载文件"
                        })
            
            return sorted(files, key=lambda x: x["modified_at"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
            return []
    
    def delete_graph(self, file_path: Union[str, Path]) -> bool:
        """删除知识图谱文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否删除成功
        """
        try:
            file_path = Path(file_path)
            
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"文件已删除: {file_path}")
                return True
            else:
                self.logger.warning(f"文件不存在: {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
            return False
