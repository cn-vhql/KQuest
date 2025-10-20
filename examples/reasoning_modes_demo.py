#!/usr/bin/env python3
"""推理模式对比演示脚本"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.kquest.models import KnowledgeGraph, KnowledgeTriple, TripleType

def create_sample_knowledge_graph():
    """创建示例知识图谱"""
    triples = [
        KnowledgeTriple(
            subject="人工智能",
            predicate="包含",
            object="机器学习",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.95
        ),
        KnowledgeTriple(
            subject="机器学习",
            predicate="包含",
            object="深度学习",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.90
        ),
        KnowledgeTriple(
            subject="深度学习",
            predicate="使用",
            object="神经网络",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.92
        ),
        KnowledgeTriple(
            subject="神经网络",
            predicate="模拟",
            object="人脑结构",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.85
        ),
        KnowledgeTriple(
            subject="Python",
            predicate="适合",
            object="AI开发",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.88
        ),
        KnowledgeTriple(
            subject="机器学习",
            predicate="需要",
            object="大量数据",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.83
        ),
    ]

    return KnowledgeGraph(triples=triples)

def demo_reasoning_modes():
    """演示三种推理模式"""
    print("🧠 KQuest 推理模式对比演示")
    print("=" * 50)

    # 创建示例知识图谱
    kg = create_sample_knowledge_graph()
    print(f"📊 创建示例知识图谱：{len(kg.triples)} 个三元组")

    print("\n📝 示例问题：")
    questions = [
        "什么是深度学习？",
        "Python和AI有什么关系？",
        "机器学习需要什么？"
    ]

    for i, question in enumerate(questions, 1):
        print(f"{i}. {question}")

    print("\n🎯 推理模式说明：")
    print("📊 纯图算法模式：")
    print("  - 速度：⚡ 极快")
    print("  - 质量：⭐ 基础")
    print("  - 特点：基于图结构进行路径查找和实体匹配")
    print("  - 适用：简单关系查询、事实查找")

    print("\n🔗 混合推理模式：")
    print("  - 速度：🚶 中等")
    print("  - 质量：⭐⭐ 高")
    print("  - 特点：结合图算法和LLM语义理解")
    print("  - 适用：一般性问题、需要理解语义的场景")

    print("\n🚀 LLM驱动模式：")
    print("  - 速度：🐌 较慢")
    print("  - 质量：⭐⭐⭐ 最高")
    print("  - 特点：以大模型为主，图谱为知识库")
    print("  - 适用：复杂分析、多步推理、深度解释")

    print("\n💡 使用建议：")
    print("- 🔍 简单查询 → 使用 📊 纯图算法")
    print("- 🎯 日常使用 → 选择 🔗 混合推理")
    print("- 🤔 复杂问题 → 尝试 🚀 LLM驱动")

    print("\n🌐 Web UI 体验：")
    print("启动 Web UI：python run_web.py")
    print("在智能问答页面可以自由切换三种推理模式，实时体验效果差异！")

if __name__ == "__main__":
    demo_reasoning_modes()