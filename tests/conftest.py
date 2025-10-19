"""pytest配置文件"""

import pytest
import tempfile
import shutil
from pathlib import Path
from kquest.config import Config
from kquest.models import KnowledgeTriple, KnowledgeGraph, TripleType


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config():
    """测试配置"""
    return Config(
        project_name="KQuest Test",
        version="0.1.0",
        debug=True,
        openai={
            "api_key": "test-api-key",
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 1000,
            "timeout": 30,
            "max_retries": 2,
            "retry_delay": 0.5
        },
        extraction={
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "max_chunks_per_request": 2,
            "min_confidence": 0.5,
            "enable_filtering": True,
            "language": "zh"
        },
        reasoning={
            "max_reasoning_depth": 2,
            "max_triples_per_query": 10,
            "enable_fuzzy_matching": True,
            "similarity_threshold": 0.7,
            "reasoning_model": "gpt-3.5-turbo"
        },
        storage={
            "default_format": "json",
            "output_dir": "test_output",
            "backup_enabled": False,
            "compression": False
        },
        logging={
            "level": "DEBUG",
            "console_output": False
        }
    )


@pytest.fixture
def sample_triples():
    """示例三元组数据"""
    return [
        KnowledgeTriple(
            subject="人工智能",
            predicate="是",
            object="计算机科学分支",
            triple_type=TripleType.CLASS_RELATION,
            confidence=0.9
        ),
        KnowledgeTriple(
            subject="机器学习",
            predicate="是",
            object="人工智能子领域",
            triple_type=TripleType.CLASS_RELATION,
            confidence=0.8
        ),
        KnowledgeTriple(
            subject="深度学习",
            predicate="基于",
            object="神经网络",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.85
        ),
        KnowledgeTriple(
            subject="杰弗里·辛顿",
            predicate="被称为",
            object="深度学习之父",
            triple_type=TripleType.ENTITY_ATTRIBUTE,
            confidence=0.9
        )
    ]


@pytest.fixture
def sample_knowledge_graph(sample_triples):
    """示例知识图谱"""
    return KnowledgeGraph(triples=sample_triples)


@pytest.fixture
def sample_text():
    """示例文本"""
    return """
    人工智能（Artificial Intelligence，AI）是计算机科学的一个分支。
    机器学习是人工智能的核心分支之一。
    深度学习基于神经网络，在图像识别等领域表现出色。
    杰弗里·辛顿被称为深度学习之父。
    """


@pytest.fixture
def sample_markdown_file(temp_dir, sample_text):
    """创建示例Markdown文件"""
    file_path = temp_dir / "sample.md"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(sample_text)
    return file_path
