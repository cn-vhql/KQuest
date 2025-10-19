#!/usr/bin/env python3
"""
KQuest 使用示例
演示如何使用KQuest进行知识图谱抽取和问答
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from kquest import KnowledgeExtractor, KnowledgeReasoner, KnowledgeStorage, Config
from kquest.models import KnowledgeGraph, KnowledgeTriple, TripleType


def load_example_config():
    """加载示例配置"""
    config_data = {
        "project_name": "KQuest Example",
        "version": "0.1.0",
        "debug": True,
        "openai": {
            "api_key": "your-api-key-here",  # 请替换为实际的API密钥
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 2000,
            "timeout": 60,
            "max_retries": 3,
            "retry_delay": 1.0
        },
        "extraction": {
            "chunk_size": 1500,
            "chunk_overlap": 200,
            "max_chunks_per_request": 3,
            "min_confidence": 0.5,
            "enable_filtering": True,
            "language": "zh"
        },
        "reasoning": {
            "max_reasoning_depth": 3,
            "max_triples_per_query": 15,
            "enable_fuzzy_matching": True,
            "similarity_threshold": 0.7,
            "reasoning_model": "gpt-3.5-turbo"
        },
        "storage": {
            "default_format": "json",
            "output_dir": "examples/output",
            "backup_enabled": True,
            "compression": False
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "console_output": True
        }
    }
    
    return Config(**config_data)


async def example_extraction():
    """示例：知识抽取"""
    print("=" * 60)
    print("示例1: 知识图谱抽取")
    print("=" * 60)
    
    # 加载配置
    config = load_example_config()
    
    # 检查API密钥
    if config.openai.api_key == "your-api-key-here":
        print("❌ 请先配置OpenAI API密钥")
        print("   在config/config.yaml中设置openai.api_key，或设置环境变量OPENAI_API_KEY")
        return
    
    # 创建抽取器
    extractor = KnowledgeExtractor(config)
    
    # 读取示例文本
    sample_file = Path(__file__).parent / "sample_text.md"
    with open(sample_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"📖 读取文件: {sample_file}")
    print(f"📝 文本长度: {len(text)} 字符")
    print()
    
    # 执行抽取
    print("🔄 开始抽取知识图谱...")
    result = await extractor.extract_from_text(text, str(sample_file))
    
    if result.success:
        print(f"✅ 抽取成功!")
        print(f"   - 处理时间: {result.processing_time:.2f}秒")
        print(f"   - 抽取三元组: {result.extracted_triples}个")
        print()
        
        # 显示部分三元组
        print("📊 抽取的三元组示例:")
        for i, triple in enumerate(result.knowledge_graph.triples[:5], 1):
            print(f"   {i}. {triple}")
        
        if len(result.knowledge_graph.triples) > 5:
            print(f"   ... 还有{len(result.knowledge_graph.triples) - 5}个三元组")
        
        print()
        
        # 保存知识图谱
        storage = KnowledgeStorage(config)
        output_file = Path("examples/output/ai_knowledge_graph.json")
        
        if storage.save_knowledge_graph(result.knowledge_graph, output_file):
            print(f"💾 知识图谱已保存到: {output_file}")
        
        return result.knowledge_graph
    else:
        print(f"❌ 抽取失败: {result.error_message}")
        return None


async def example_querying(knowledge_graph):
    """示例：知识问答"""
    print("\n" + "=" * 60)
    print("示例2: 知识问答")
    print("=" * 60)
    
    if not knowledge_graph:
        print("❌ 没有可用的知识图谱，跳过问答示例")
        return
    
    # 加载配置
    config = load_example_config()
    
    # 检查API密钥
    if config.openai.api_key == "your-api-key-here":
        print("❌ 请先配置OpenAI API密钥")
        return
    
    # 创建推理器
    reasoner = KnowledgeReasoner(config)
    
    # 示例问题
    questions = [
        "什么是人工智能？",
        "人工智能的主要分支有哪些？",
        "杰弗里·辛顿有什么贡献？",
        "人工智能在医疗领域有什么应用？"
    ]
    
    print("🤔 开始问答演示:")
    print()
    
    for i, question in enumerate(questions, 1):
        print(f"问题 {i}: {question}")
        print("-" * 40)
        
        # 查询
        result = await reasoner.query(question, knowledge_graph)
        
        print(f"回答: {result.answer}")
        print(f"置信度: {result.confidence:.2f}")
        
        if result.reasoning_path:
            print("推理过程:")
            for j, step in enumerate(result.reasoning_path, 1):
                print(f"  {j}. {step}")
        
        if result.source_triples:
            print("来源三元组:")
            for j, triple in enumerate(result.source_triples, 1):
                print(f"  {j}. {triple}")
        
        print()


def example_storage():
    """示例：存储管理"""
    print("=" * 60)
    print("示例3: 存储管理")
    print("=" * 60)
    
    # 加载配置
    config = load_example_config()
    
    # 创建存储管理器
    storage = KnowledgeStorage(config)
    
    # 创建示例知识图谱
    triples = [
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
            object="人工智能分支",
            triple_type=TripleType.CLASS_RELATION,
            confidence=0.9
        ),
        KnowledgeTriple(
            subject="深度学习",
            predicate="基于",
            object="神经网络",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.8
        ),
        KnowledgeTriple(
            subject="杰弗里·辛顿",
            predicate="被称为",
            object="深度学习之父",
            triple_type=TripleType.ENTITY_ATTRIBUTE,
            confidence=0.9
        )
    ]
    
    knowledge_graph = KnowledgeGraph(triples=triples)
    
    print("📊 创建示例知识图谱:")
    for i, triple in enumerate(triples, 1):
        print(f"   {i}. {triple}")
    print()
    
    # 保存为不同格式
    formats = ["json", "rdf", "csv", "ttl"]
    
    for format in formats:
        output_file = Path(f"examples/output/example_graph.{format}")
        
        if storage.save_knowledge_graph(knowledge_graph, output_file, format):
            print(f"✅ 已保存为{format.upper()}格式: {output_file}")
        else:
            print(f"❌ 保存{format.upper()}格式失败")
    
    print()
    
    # 列出已保存的文件
    print("📁 已保存的知识图谱文件:")
    files = storage.list_saved_graphs()
    
    if files:
        for file_info in files[:5]:  # 只显示前5个
            print(f"   • {file_info['name']} ({file_info['format']}, {file_info['triples_count']}个三元组)")
    else:
        print("   没有找到文件")


def example_manual_creation():
    """示例：手动创建知识图谱"""
    print("\n" + "=" * 60)
    print("示例4: 手动创建知识图谱")
    print("=" * 60)
    
    # 手动创建三元组
    triples = [
        KnowledgeTriple(
            subject="Python",
            predicate="是",
            object="编程语言",
            triple_type=TripleType.CLASS_RELATION,
            confidence=1.0,
            metadata={"source": "manual"}
        ),
        KnowledgeTriple(
            subject="Python",
            predicate="适用于",
            object="数据科学",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.9,
            metadata={"source": "manual"}
        ),
        KnowledgeTriple(
            subject="Python",
            predicate="创建者",
            object="Guido van Rossum",
            triple_type=TripleType.ENTITY_ATTRIBUTE,
            confidence=1.0,
            metadata={"source": "manual"}
        )
    ]
    
    # 创建知识图谱
    knowledge_graph = KnowledgeGraph(triples=triples)
    
    print("🔧 手动创建的知识图谱:")
    for i, triple in enumerate(triples, 1):
        print(f"   {i}. {triple}")
    
    # 获取统计信息
    stats = knowledge_graph.get_statistics()
    print(f"\n📈 统计信息:")
    print(f"   • 总三元组数: {stats['total_triples']}")
    print(f"   • 唯一主语数: {stats['unique_subjects']}")
    print(f"   • 唯一宾语数: {stats['unique_objects']}")
    print(f"   • 唯一谓语数: {stats['unique_predicates']}")
    
    # 查找特定实体的三元组
    print(f"\n🔍 查找'Python'相关的三元组:")
    python_triples = knowledge_graph.find_triples_by_subject("Python")
    for triple in python_triples:
        print(f"   • {triple}")


async def main():
    """主函数"""
    print("🚀 KQuest 使用示例")
    print("=" * 60)
    
    # 确保输出目录存在
    output_dir = Path("examples/output")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # 示例1: 知识抽取
        knowledge_graph = await example_extraction()
        
        # 示例2: 知识问答
        await example_querying(knowledge_graph)
        
        # 示例3: 存储管理
        example_storage()
        
        # 示例4: 手动创建
        example_manual_creation()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 运行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
