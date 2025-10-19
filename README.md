# KQuest - 知识图谱抽取与问答系统

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

KQuest是一个基于大语言模型的生产级知识图谱抽取和智能问答系统，支持从文本文件中高效抽取知识图谱三元组，并基于知识推理回答用户问题。

## ✨ 功能特性

- 📄 **多格式文本支持**: 支持从Markdown、TXT等文本文件中抽取知识
- 🧠 **智能三元组抽取**: 基于大语言模型高效抽取高质量知识图谱三元组
- 💾 **标准格式存储**: 支持多种标准知识图谱格式（RDF、JSON-LD、CSV、Turtle等）
- 🤖 **知识推理问答**: 结合知识图谱进行智能问答和推理
- ⚙️ **灵活配置**: 通过配置文件管理模型参数和行为
- 💻 **CLI交互**: 友好的命令行界面，支持批量和交互式操作
- 🔍 **质量控制**: 内置置信度评估和结果过滤机制
- 📊 **统计分析**: 提供详细的知识图谱统计和分析功能
- 🚀 **高性能**: 支持异步处理和批量操作
- 🛡️ **生产就绪**: 完善的错误处理、日志记录和测试覆盖

## 🏗️ 技术栈

- **语言**: Python 3.11+
- **大模型**: OpenAI API (GPT-3.5, GPT-4等)
- **知识图谱**: RDFLib, NetworkX
- **CLI**: Click, Rich
- **配置管理**: Pydantic, PyYAML
- **数据处理**: Pydantic, asyncio
- **测试**: pytest
- **代码质量**: black, isort, mypy, flake8

## 🚀 快速开始

### 1. 安装

```bash
# 克隆项目
git clone <repository-url>
cd KQuest

# 安装依赖
uv sync

### 2. 配置

```bash
# 复制配置文件模板
cp config/config.yaml.example config/config.yaml

# 编辑配置文件，设置OpenAI API密钥
vim config/config.yaml
```

或在环境变量中设置：
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 3. 第一次使用

```bash
# 从文本文件抽取知识图谱
kquest extract --input examples/sample_text.md --output output/kg.json

# 基于知识图谱回答问题
kquest query --kg output/kg.json --question "什么是人工智能？"

# 交互式问答模式
kquest query --kg output/kg.json --interactive
```

## 📖 详细文档

- [用户指南](docs/user_guide.md) - 完整的使用说明和最佳实践
- [API文档](docs/api.md) - Python API参考
- [配置说明](docs/configuration.md) - 详细的配置选项
- [开发指南](docs/development.md) - 贡献代码和扩展功能

## 💻 命令行接口

### 知识抽取
```bash
# 基本抽取
kquest extract -i document.md -o knowledge.json

# 指定格式和参数
kquest extract -i document.md -o knowledge.rdf -f rdf -l zh -d "计算机科学"

# 启用压缩
kquest extract -i document.md -o knowledge.json.gz --compress
```

### 知识问答
```bash
# 单次查询
kquest query --kg knowledge.json --question "机器学习的原理是什么？"

# 交互式查询
kquest query --kg knowledge.json --interactive

# 查看知识图谱信息
kquest info --kg knowledge.json
```

### 文件管理
```bash
# 列出所有知识图谱
kquest list

# 转换格式
kquest convert knowledge.json knowledge.rdf --to-format rdf

# 查看配置
kquest config-show
```

## 🐍 Python API

### 基本用法
```python
from kquest import KnowledgeExtractor, KnowledgeReasoner, KnowledgeStorage

# 创建组件
extractor = KnowledgeExtractor()
reasoner = KnowledgeReasoner()
storage = KnowledgeStorage()

# 知识抽取
result = extractor.extract_from_file_sync("document.md")
if result.success:
    kg = result.knowledge_graph
    
    # 保存知识图谱
    storage.save_knowledge_graph(kg, "output.json")
    
    # 知识问答
    answer = reasoner.query_sync("什么是AI？", kg)
    print(f"回答: {answer.answer}")
```

### 异步用法
```python
import asyncio
from kquest import KnowledgeExtractor, KnowledgeReasoner

async def main():
    extractor = KnowledgeExtractor()
    reasoner = KnowledgeReasoner()
    
    # 异步抽取
    result = await extractor.extract_from_file("document.md")
    
    if result.success:
        # 异步查询
        answer = await reasoner.query("AI的应用有哪些？", result.knowledge_graph)
        print(answer.answer)

asyncio.run(main())
```

## 📁 项目结构

```
KQuest/
├── src/
│   └── kquest/
│       ├── __init__.py           # 包初始化
│       ├── cli.py                # CLI命令行接口
│       ├── config.py             # 配置管理
│       ├── extractor.py          # 知识抽取器
│       ├── reasoning.py          # 知识推理引擎
│       ├── storage.py            # 存储管理
│       └── models.py             # 数据模型定义
├── config/
│   ├── config.yaml.example       # 配置文件模板
│   └── prompts.yaml              # 提示词模板
├── tests/
│   ├── test_models.py            # 模型测试
│   ├── test_extractor.py         # 抽取器测试
│   ├── test_reasoning.py         # 推理测试
│   └── conftest.py               # 测试配置
├── examples/
│   ├── sample_text.md            # 示例文本
│   └── example_usage.py          # 使用示例
├── docs/
│   ├── user_guide.md             # 用户指南
│   ├── api.md                    # API文档
│   ├── configuration.md          # 配置说明
│   └── development.md            # 开发指南
├── pyproject.toml                # 项目配置
├── README.md                     # 项目说明
└── .gitignore                    # Git忽略文件
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_models.py

# 运行测试并生成覆盖率报告
pytest --cov=kquest --cov-report=html

# 代码格式检查
black --check src/ tests/
isort --check-only src/ tests/

# 类型检查
mypy src/
```

## 🔧 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd KQuest

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 安装pre-commit钩子
pre-commit install

# 运行示例
python examples/example_usage.py
```

## 📊 示例输出

### 知识抽取结果
```json
{
  "metadata": {
    "total_triples": 15,
    "created_at": "2024-01-01T12:00:00"
  },
  "triples": [
    {
      "subject": "人工智能",
      "predicate": "是",
      "object": "计算机科学分支",
      "triple_type": "class_relation",
      "confidence": 0.9
    }
  ]
}
```

### 问答结果
```
问题: 什么是深度学习？
回答: 深度学习是机器学习的一个子领域，基于人工神经网络...
置信度: 0.85
推理过程:
1. 分析问题中的关键概念"深度学习"
2. 在知识图谱中查找相关三元组
3. 找到"深度学习"与"机器学习"的关系
4. 综合信息给出完整回答
```

## 🤝 贡献指南

我们欢迎各种形式的贡献！请查看 [开发指南](docs/development.md) 了解详细信息。

### 贡献方式
- 🐛 报告Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ✨ 添加新功能

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- OpenAI 提供强大的语言模型API
- RDFLib 社区提供的优秀知识图谱工具
- 所有贡献者和用户的支持

## 📞 联系我们

- 📧 Email: [yl_zhangqiang@foxmail.com]
- 🐛 Issues: [GitHub Issues](https://github.com/cn-vhql/KQuest/issues)
- 📖 Wiki: [项目Wiki](https://github.com/cn-vhql/KQuest/wiki)

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！
