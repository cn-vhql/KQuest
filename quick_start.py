#!/usr/bin/env python3
"""
KQuest 快速开始脚本
运行此脚本快速体验KQuest的功能
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def check_requirements():
    """检查基本要求"""
    print("🔍 检查系统要求...")
    
    # 检查Python版本
    if sys.version_info < (3, 11):
        print("❌ Python版本过低，需要Python 3.11+")
        return False
    
    print(f"✅ Python版本: {sys.version.split()[0]}")
    
    # 检查必要的包
    required_packages = [
        "pydantic", "click", "openai", "rdflib", 
        "rich", "pyyaml", "typer"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")
    
    if missing_packages:
        print(f"\n请安装缺失的包: pip install {' '.join(missing_packages)}")
        return False
    
    return True


def check_config():
    """检查配置"""
    print("\n🔧 检查配置...")
    
    config_file = project_root / "config" / "config.yaml"
    
    if not config_file.exists():
        print("⚠️  配置文件不存在，正在创建...")
        
        # 复制模板文件
        template_file = project_root / "config" / "config.yaml.example"
        if template_file.exists():
            import shutil
            shutil.copy(template_file, config_file)
            print("✅ 已创建配置文件模板")
        else:
            print("❌ 配置文件模板不存在")
            return False
    
    # 检查API密钥
    try:
        from kquest.config import get_config
        
        config = get_config()
        
        if not config.openai.api_key or config.openai.api_key == "your-openai-api-key-here":
            print("⚠️  请设置OpenAI API密钥")
            print("   方法1: 编辑 config/config.yaml 文件")
            print("   方法2: 设置环境变量 OPENAI_API_KEY")
            print("   方法3: 在运行时输入API密钥")
            
            choice = input("\n选择设置方式 (1/2/3): ").strip()
            
            if choice == "1":
                print(f"请编辑文件: {config_file}")
                return False
            elif choice == "2":
                api_key = input("请输入OpenAI API密钥: ").strip()
                os.environ["OPENAI_API_KEY"] = api_key
                print("✅ 已设置环境变量")
            elif choice == "3":
                api_key = input("请输入OpenAI API密钥: ").strip()
                if api_key:
                    # 临时修改配置
                    config.openai.api_key = api_key
                    print("✅ 已设置API密钥")
                else:
                    print("❌ API密钥不能为空")
                    return False
        else:
            print("✅ API密钥已配置")
    
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False
    
    return True


async def demo_extraction():
    """演示知识抽取"""
    print("\n📚 演示知识抽取...")
    
    try:
        from kquest import KnowledgeExtractor, KnowledgeStorage
        
        # 读取示例文本
        sample_file = project_root / "examples" / "sample_text.md"
        if not sample_file.exists():
            print("❌ 示例文件不存在")
            return False
        
        with open(sample_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"📖 读取示例文件: {sample_file.name}")
        print(f"📝 文本长度: {len(text)} 字符")
        
        # 创建抽取器
        extractor = KnowledgeExtractor()
        
        print("🔄 开始抽取知识图谱...")
        result = await extractor.extract_from_text(text, str(sample_file))
        
        if result.success:
            print(f"✅ 抽取成功!")
            print(f"   - 处理时间: {result.processing_time:.2f}秒")
            print(f"   - 抽取三元组: {result.extracted_triples}个")
            
            # 显示部分三元组
            print("\n📊 抽取的三元组示例:")
            for i, triple in enumerate(result.knowledge_graph.triples[:3], 1):
                print(f"   {i}. {triple}")
            
            if len(result.knowledge_graph.triples) > 3:
                print(f"   ... 还有{len(result.knowledge_graph.triples) - 3}个三元组")
            
            # 保存知识图谱
            output_dir = project_root / "output"
            output_dir.mkdir(exist_ok=True)
            
            storage = KnowledgeStorage()
            output_file = output_dir / "demo_knowledge_graph.json"
            
            if storage.save_knowledge_graph(result.knowledge_graph, output_file):
                print(f"\n💾 知识图谱已保存到: {output_file}")
                return str(output_file)
            else:
                print("❌ 保存知识图谱失败")
                return False
        else:
            print(f"❌ 抽取失败: {result.error_message}")
            return False
    
    except Exception as e:
        print(f"❌ 抽取过程中出现错误: {e}")
        return False


async def demo_querying(kg_file):
    """演示知识问答"""
    print("\n🤔 演示知识问答...")
    
    try:
        from kquest import KnowledgeReasoner, KnowledgeStorage
        
        # 加载知识图谱
        storage = KnowledgeStorage()
        knowledge_graph = storage.load_knowledge_graph(kg_file)
        
        if not knowledge_graph:
            print("❌ 无法加载知识图谱")
            return False
        
        print(f"✅ 知识图谱加载成功，包含 {len(knowledge_graph.triples)} 个三元组")
        
        # 创建推理器
        reasoner = KnowledgeReasoner()
        
        # 示例问题
        questions = [
            "什么是人工智能？",
            "机器学习有哪些类型？",
            "深度学习基于什么技术？"
        ]
        
        print("\n开始问答演示:")
        
        for i, question in enumerate(questions, 1):
            print(f"\n问题 {i}: {question}")
            print("-" * 40)
            
            # 查询
            result = await reasoner.query(question, knowledge_graph)
            
            print(f"回答: {result.answer}")
            print(f"置信度: {result.confidence:.2f}")
        
        return True
    
    except Exception as e:
        print(f"❌ 问答过程中出现错误: {e}")
        return False


def demo_cli():
    """演示CLI命令"""
    print("\n💻 演示CLI命令...")
    
    # 检查是否有知识图谱文件
    kg_file = project_root / "output" / "demo_knowledge_graph.json"
    if not kg_file.exists():
        print("❌ 没有可用的知识图谱文件，请先运行抽取演示")
        return False
    
    print("✅ 可以使用以下CLI命令:")
    print()
    
    print("1. 查看知识图谱信息:")
    print(f"   kquest info --kg {kg_file}")
    print()
    
    print("2. 列出所有知识图谱文件:")
    print("   kquest list")
    print()
    
    print("3. 交互式问答:")
    print(f"   kquest query --kg {kg_file} --interactive")
    print()
    
    print("4. 单次查询:")
    print(f"   kquest query --kg {kg_file} --question \"什么是深度学习？\"")
    print()
    
    print("5. 转换格式:")
    print(f"   kquest convert {kg_file} output/demo_knowledge.rdf --to-format rdf")
    print()
    
    return True


def show_next_steps():
    """显示后续步骤"""
    print("\n🎉 演示完成！")
    print("\n📚 后续步骤:")
    print("1. 阅读用户指南: docs/user_guide.md")
    print("2. 查看更多示例: examples/")
    print("3. 运行测试: pytest")
    print("4. 使用自己的文档进行抽取")
    print("5. 探索不同的配置选项")
    print()
    
    print("🔗 有用的链接:")
    print("- 用户指南: docs/user_guide.md")
    print("- 配置说明: config/config.yaml.example")
    print("- 示例代码: examples/example_usage.py")
    print("- 项目文档: docs/")
    print()


async def main():
    """主函数"""
    print("🚀 KQuest 快速开始")
    print("=" * 50)
    
    # 检查要求
    if not check_requirements():
        print("\n❌ 系统要求检查失败，请解决上述问题后重试")
        return
    
    # 检查配置
    if not check_config():
        print("\n❌ 配置检查失败，请解决上述问题后重试")
        return
    
    print("\n✅ 系统检查通过，开始演示...")
    
    try:
        # 知识抽取演示
        kg_file = await demo_extraction()
        if not kg_file:
            print("\n❌ 知识抽取演示失败")
            return
        
        # 知识问答演示
        if not await demo_querying(kg_file):
            print("\n❌ 知识问答演示失败")
            return
        
        # CLI演示
        demo_cli()
        
        # 显示后续步骤
        show_next_steps()
        
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行快速开始演示
    asyncio.run(main())
