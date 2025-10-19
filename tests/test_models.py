"""测试数据模型"""

import pytest
from datetime import datetime
from kquest.models import (
    KnowledgeTriple,
    KnowledgeGraph,
    QueryResult,
    TripleType,
    ConfidenceLevel,
    ExtractionResult,
    DocumentChunk,
    TaskStatus,
    ProcessingStatus
)


class TestKnowledgeTriple:
    """测试KnowledgeTriple模型"""
    
    def test_triple_creation(self):
        """测试三元组创建"""
        triple = KnowledgeTriple(
            subject="人工智能",
            predicate="是",
            object="计算机科学分支",
            triple_type=TripleType.CLASS_RELATION,
            confidence=0.9
        )
        
        assert triple.subject == "人工智能"
        assert triple.predicate == "是"
        assert triple.object == "计算机科学分支"
        assert triple.triple_type == TripleType.CLASS_RELATION
        assert triple.confidence == 0.9
        assert triple.confidence_level == ConfidenceLevel.HIGH
    
    def test_confidence_level_auto_assignment(self):
        """测试置信度级别自动分配"""
        # 高置信度
        triple_high = KnowledgeTriple(
            subject="A", predicate="是", object="B",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.9
        )
        assert triple_high.confidence_level == ConfidenceLevel.HIGH
        
        # 中等置信度
        triple_medium = KnowledgeTriple(
            subject="A", predicate="是", object="B",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.6
        )
        assert triple_medium.confidence_level == ConfidenceLevel.MEDIUM
        
        # 低置信度
        triple_low = KnowledgeTriple(
            subject="A", predicate="是", object="B",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.3
        )
        assert triple_low.confidence_level == ConfidenceLevel.LOW
    
    def test_triple_string_representation(self):
        """测试三元组字符串表示"""
        triple = KnowledgeTriple(
            subject="北京", predicate="是...的首都", object="中国",
            triple_type=TripleType.ENTITY_RELATION
        )
        expected = "北京 --是...的首都--> 中国"
        assert str(triple) == expected
    
    def test_to_rdf_tuple(self):
        """测试转换为RDF元组"""
        triple = KnowledgeTriple(
            subject="Python", predicate="是", object="编程语言",
            triple_type=TripleType.CLASS_RELATION
        )
        rdf_tuple = triple.to_rdf_tuple()
        assert rdf_tuple == ("Python", "是", "编程语言")


class TestKnowledgeGraph:
    """测试KnowledgeGraph模型"""
    
    def test_graph_creation(self):
        """测试知识图谱创建"""
        graph = KnowledgeGraph()
        assert len(graph.triples) == 0
        assert isinstance(graph.created_at, datetime)
        assert isinstance(graph.updated_at, datetime)
    
    def test_add_triple(self):
        """测试添加三元组"""
        graph = KnowledgeGraph()
        triple = KnowledgeTriple(
            subject="AI", predicate="是", object="人工智能",
            triple_type=TripleType.ENTITY_ATTRIBUTE
        )
        
        initial_count = len(graph.triples)
        graph.add_triple(triple)
        
        assert len(graph.triples) == initial_count + 1
        assert triple in graph.triples
    
    def test_remove_triple(self):
        """测试删除三元组"""
        graph = KnowledgeGraph()
        triple = KnowledgeTriple(
            subject="AI", predicate="是", object="人工智能",
            triple_type=TripleType.ENTITY_ATTRIBUTE
        )
        graph.add_triple(triple)
        
        # 删除存在的三元组
        success = graph.remove_triple(0)
        assert success
        assert len(graph.triples) == 0
        
        # 删除不存在的三元组
        success = graph.remove_triple(0)
        assert not success
    
    def test_get_subjects(self):
        """测试获取所有主语"""
        graph = KnowledgeGraph()
        triples = [
            KnowledgeTriple(subject="A", predicate="p1", object="X", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="B", predicate="p2", object="Y", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="A", predicate="p3", object="Z", triple_type=TripleType.ENTITY_RELATION),
        ]
        
        for triple in triples:
            graph.add_triple(triple)
        
        subjects = graph.get_subjects()
        assert set(subjects) == {"A", "B"}
    
    def test_get_objects(self):
        """测试获取所有宾语"""
        graph = KnowledgeGraph()
        triples = [
            KnowledgeTriple(subject="A", predicate="p1", object="X", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="B", predicate="p2", object="Y", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="C", predicate="p3", object="X", triple_type=TripleType.ENTITY_RELATION),
        ]
        
        for triple in triples:
            graph.add_triple(triple)
        
        objects = graph.get_objects()
        assert set(objects) == {"X", "Y"}
    
    def test_get_predicates(self):
        """测试获取所有谓语"""
        graph = KnowledgeGraph()
        triples = [
            KnowledgeTriple(subject="A", predicate="是", object="X", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="B", predicate="属于", object="Y", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="C", predicate="是", object="Z", triple_type=TripleType.ENTITY_RELATION),
        ]
        
        for triple in triples:
            graph.add_triple(triple)
        
        predicates = graph.get_predicates()
        assert set(predicates) == {"是", "属于"}
    
    def test_find_triples_by_subject(self):
        """测试根据主语查找三元组"""
        graph = KnowledgeGraph()
        triples = [
            KnowledgeTriple(subject="AI", predicate="是", object="人工智能", triple_type=TripleType.ENTITY_ATTRIBUTE),
            KnowledgeTriple(subject="AI", predicate="应用于", object="医疗", triple_type=TripleType.ENTITY_RELATION),
            KnowledgeTriple(subject="ML", predicate="是", object="机器学习", triple_type=TripleType.ENTITY_ATTRIBUTE),
        ]
        
        for triple in triples:
            graph.add_triple(triple)
        
        ai_triples = graph.find_triples_by_subject("AI")
        assert len(ai_triples) == 2
        assert all(triple.subject == "AI" for triple in ai_triples)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        graph = KnowledgeGraph()
        triples = [
            KnowledgeTriple(subject="A", predicate="是", object="B", triple_type=TripleType.ENTITY_RELATION, confidence=0.9),
            KnowledgeTriple(subject="C", predicate="属于", object="D", triple_type=TripleType.CLASS_RELATION, confidence=0.6),
            KnowledgeTriple(subject="E", predicate="有", object="属性", triple_type=TripleType.ENTITY_ATTRIBUTE, confidence=0.3),
        ]
        
        for triple in triples:
            graph.add_triple(triple)
        
        stats = graph.get_statistics()
        
        assert stats["total_triples"] == 3
        assert stats["unique_subjects"] == 3
        assert stats["unique_objects"] == 3
        assert stats["unique_predicates"] == 3
        assert stats["triple_types"]["entity_relation"] == 1
        assert stats["triple_types"]["class_relation"] == 1
        assert stats["triple_types"]["entity_attribute"] == 1
        assert stats["confidence_distribution"]["high"] == 1
        assert stats["confidence_distribution"]["medium"] == 1
        assert stats["confidence_distribution"]["low"] == 1


class TestQueryResult:
    """测试QueryResult模型"""
    
    def test_query_result_creation(self):
        """测试查询结果创建"""
        result = QueryResult(
            question="什么是人工智能？",
            answer="人工智能是计算机科学的一个分支...",
            confidence=0.85
        )
        
        assert result.question == "什么是人工智能？"
        assert result.answer == "人工智能是计算机科学的一个分支..."
        assert result.confidence == 0.85
        assert len(result.source_triples) == 0
        assert len(result.reasoning_path) == 0
    
    def test_add_source_triple(self):
        """测试添加来源三元组"""
        result = QueryResult(
            question="测试问题",
            answer="测试回答",
            confidence=0.8
        )
        
        triple = KnowledgeTriple(
            subject="AI", predicate="是", object="人工智能",
            triple_type=TripleType.ENTITY_ATTRIBUTE
        )
        
        result.add_source_triple(triple)
        assert len(result.source_triples) == 1
        assert triple in result.source_triples
        
        # 测试重复添加
        result.add_source_triple(triple)
        assert len(result.source_triples) == 1  # 不应该重复
    
    def test_add_reasoning_step(self):
        """测试添加推理步骤"""
        result = QueryResult(
            question="测试问题",
            answer="测试回答",
            confidence=0.8
        )
        
        result.add_reasoning_step("步骤1：分析问题")
        result.add_reasoning_step("步骤2：查找相关信息")
        
        assert len(result.reasoning_path) == 2
        assert "步骤1：分析问题" in result.reasoning_path
        assert "步骤2：查找相关信息" in result.reasoning_path


class TestDocumentChunk:
    """测试DocumentChunk模型"""
    
    def test_chunk_creation(self):
        """测试文档块创建"""
        chunk = DocumentChunk(
            content="这是测试内容",
            chunk_id="chunk_0",
            source_file="test.txt",
            start_position=0,
            end_position=6
        )
        
        assert chunk.content == "这是测试内容"
        assert chunk.chunk_id == "chunk_0"
        assert chunk.source_file == "test.txt"
        assert chunk.start_position == 0
        assert chunk.end_position == 6
    
    def test_chunk_length(self):
        """测试文档块长度"""
        chunk = DocumentChunk(
            content="Hello, 世界!",
            chunk_id="chunk_1",
            source_file="test.txt",
            start_position=0,
            end_position=9
        )
        
        assert chunk.length() == 9


class TestTaskStatus:
    """测试TaskStatus模型"""
    
    def test_task_status_creation(self):
        """测试任务状态创建"""
        task = TaskStatus(
            task_id="test_task_001",
            status=ProcessingStatus.PENDING
        )
        
        assert task.task_id == "test_task_001"
        assert task.status == ProcessingStatus.PENDING
        assert task.progress == 0.0
        assert task.message == ""
        assert task.result is None
        assert task.error is None
    
    def test_update_progress(self):
        """测试更新进度"""
        task = TaskStatus(
            task_id="test_task",
            status=ProcessingStatus.PROCESSING
        )
        
        task.update_progress(0.5, "处理中...")
        assert task.progress == 0.5
        assert task.message == "处理中..."
        
        # 测试边界值
        task.update_progress(1.5, "完成")
        assert task.progress == 1.0  # 应该被限制为1.0
        
        task.update_progress(-0.5, "错误")
        assert task.progress == 0.0  # 应该被限制为0.0
    
    def test_set_completed(self):
        """测试设置为完成状态"""
        task = TaskStatus(
            task_id="test_task",
            status=ProcessingStatus.PROCESSING
        )
        
        extraction_result = ExtractionResult(
            knowledge_graph=KnowledgeGraph(),
            source_file="test.txt",
            processing_time=1.0,
            total_characters=100,
            extracted_triples=5
        )
        
        task.set_completed(extraction_result)
        
        assert task.status == ProcessingStatus.COMPLETED
        assert task.progress == 1.0
        assert task.message == "处理完成"
        assert task.result == extraction_result
    
    def test_set_failed(self):
        """测试设置为失败状态"""
        task = TaskStatus(
            task_id="test_task",
            status=ProcessingStatus.PROCESSING
        )
        
        error_msg = "处理失败"
        task.set_failed(error_msg)
        
        assert task.status == ProcessingStatus.FAILED
        assert task.error == error_msg
        assert "处理失败" in task.message


class TestExtractionResult:
    """测试ExtractionResult模型"""
    
    def test_extraction_result_creation(self):
        """测试抽取结果创建"""
        knowledge_graph = KnowledgeGraph()
        result = ExtractionResult(
            knowledge_graph=knowledge_graph,
            source_file="test.txt",
            processing_time=2.5,
            total_characters=1000,
            extracted_triples=10
        )
        
        assert result.knowledge_graph == knowledge_graph
        assert result.source_file == "test.txt"
        assert result.processing_time == 2.5
        assert result.total_characters == 1000
        assert result.extracted_triples == 10
        assert result.success is True
        assert result.error_message is None
    
    def test_extraction_result_failure(self):
        """测试抽取失败结果"""
        knowledge_graph = KnowledgeGraph()
        result = ExtractionResult(
            knowledge_graph=knowledge_graph,
            source_file="test.txt",
            processing_time=0.5,
            total_characters=1000,
            extracted_triples=0,
            success=False,
            error_message="文件格式不支持"
        )
        
        assert result.success is False
        assert result.error_message == "文件格式不支持"
        assert result.extracted_triples == 0


if __name__ == "__main__":
    pytest.main([__file__])
