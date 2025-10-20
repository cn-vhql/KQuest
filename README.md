# KQuest - 知识图谱抽取与LLM驱动推理系统

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

KQuest是一个基于大语言模型的生产级知识图谱抽取和智能推理系统，支持从文本文件中高效抽取知识图谱三元组，并提供多种推理模式（纯图算法、混合推理、LLM驱动）来回答用户问题。

## ✨ 功能特性

- 📄 **多格式文本支持**: 支持从Markdown、TXT等文本文件中抽取知识
- 🧠 **智能三元组抽取**: 基于大语言模型高效抽取高质量知识图谱三元组
- 🤖 **多模式推理引擎**:
  - 📊 **纯图算法**: 基于传统图算法的快速推理
  - 🔗 **混合推理**: 结合LLM语义理解与图算法
  - 🚀 **LLM驱动**: 大模型为主体，智能构建搜索策略
- 💾 **标准格式存储**: 支持多种标准知识图谱格式（RDF、JSON-LD、CSV、Turtle等）
- 🧠 **智能搜索规划**: LLM自动分析查询意图，生成搜索关键词和实体策略
- 🔍 **证据驱动推理**: 基于知识图谱证据进行推理，提供置信度评估
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
- **推理引擎**: 传统图算法 + LLM混合架构
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

# 基于知识图谱回答问题（LLM驱动模式）
kquest query --kg output/kg.json --mode llm --question "什么是人工智能？"

# 交互式问答模式
kquest query --kg output/kg.json --mode llm --interactive

# 尝试不同的推理模式
kquest query --kg output/kg.json --mode graph --question "机器学习和深度学习的关系？"
kquest query --kg output/kg.json --mode hybrid --question "Python为什么适合AI开发？"
```

## 🎯 Web 界面

KQuest 提供了基于 Streamlit 的可视化 Web 界面，让您能够通过浏览器轻松使用知识图谱抽取和问答功能。

### 快速启动 Web UI

```bash
# 安装基础依赖
uv sync

# 启动 Web UI
python run_web.py

# 或直接使用 streamlit
streamlit run src/kquest/web_ui.py
```

### 可视化功能（可选）

如需完整的可视化功能，请安装额外依赖：
```bash
pip install matplotlib pandas networkx
```

然后访问 http://localhost:8501 即可使用图形界面。

> 💡 **提示**: 即使没有可视化依赖，Web UI 也能正常工作，只是图表功能会显示为文本格式。详细安装说明请参考 [安装指南](INSTALL_WEB_UI.md)。

### Web UI 功能

- **📄 知识抽取**: 上传文档，一键抽取知识三元组
- **🤖 智能问答**: 三种推理模式可选
  - 📊 **纯图算法**: 快速查询，基础质量
  - 🔗 **混合推理**: 平衡性能，高质量
  - 🚀 **LLM驱动**: 复杂分析，最高质量
- **📊 数据可视化**: 知识图谱统计信息和网络结构图
- **⚙️ 配置管理**: 可视化配置 API 参数和抽取设置
- **💬 问答历史**: 查看和管理问答记录，包含推理模式信息

详细使用说明请参考 [Web UI 使用指南](docs/web_ui.md)。

## 📖 详细文档

- [Web UI 使用指南](docs/web_ui.md) - 图形界面完整使用说明
- [用户指南](docs/user_guide.md) - 命令行使用说明和最佳实践
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
# LLM驱动查询（推荐）
kquest query --kg knowledge.json --mode llm --question "机器学习的原理是什么？"

# 混合推理查询
kquest query --kg knowledge.json --mode hybrid --question "深度学习的应用领域？"

# 纯图算法查询（快速）
kquest query --kg knowledge.json --mode graph --question "Python和机器学习的关系？"

# 交互式查询
kquest query --kg knowledge.json --mode llm --interactive

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

### LLM驱动推理（推荐）
```python
import asyncio
from src.kquest.models import KnowledgeGraph, KnowledgeTriple as Triple, TripleType
from src.kquest.llm_driven_reasoner import LLMDrivenReasoner

async def llm_driven_example():
    # 创建知识图谱
    kg = KnowledgeGraph(triples=[
        Triple(
            subject="人工智能",
            predicate="包含",
            object="机器学习",
            triple_type=TripleType.ENTITY_RELATION,
            confidence=0.9
        )
    ])

    # 创建LLM驱动推理器
    reasoner = LLMDrivenReasoner(kg)

    # 执行推理
    result = await reasoner.query("什么是人工智能？", kg)

    print(f"回答: {result.answer}")
    print(f"置信度: {result.confidence}")
    print(f"推理过程: {result.reasoning_process}")
    print(f"信息来源: {result.sources}")

asyncio.run(llm_driven_example())
```

### 多模式推理
```python
from src.kquest.models import KnowledgeGraph, KnowledgeTriple as Triple, TripleType
from src.kquest.reasoning import KnowledgeReasoner

# 创建知识图谱
kg = KnowledgeGraph(triples=[
    Triple(subject="深度学习", predicate="是", object="机器学习技术",
           triple_type=TripleType.ENTITY_RELATION, confidence=0.9)
])

# 创建推理器（可选择不同模式）
modes = ["graph", "hybrid", "llm_driven"]
mode_names = ["纯图算法", "混合推理", "LLM驱动"]

for mode, name in zip(modes, mode_names):
    reasoner = KnowledgeReasoner(knowledge_graph=kg, reasoning_mode=mode)
    result = reasoner.query_sync("什么是深度学习？", kg)

    print(f"{name}:")
    print(f"  回答: {result.answer}")
    print(f"  置信度: {result.confidence}")
    print(f"  方法: {result.metadata.get('method')}")
```

### 基本用法
```python
from src.kquest.extractor import KnowledgeExtractor
from src.kquest.reasoning import KnowledgeReasoner
from src.kquest.storage import KnowledgeStorage

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

    # 知识问答（LLM驱动）
    answer = reasoner.query_sync("什么是AI？", kg)
    print(f"回答: {answer.answer}")
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
│       ├── reasoning.py          # 统一推理引擎
│       ├── llm_driven_reasoner.py # LLM驱动推理器
│       ├── hybrid_reasoner.py    # 混合推理器
│       ├── graph_reasoner.py     # 图算法推理器
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
│   ├── example_usage.py          # 使用示例
│   └── llm_driven_example.py     # LLM驱动示例
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
      "triple_type": "entity_relation",
      "confidence": 0.9
    }
  ]
}
```

### LLM驱动问答结果
```
问题: 什么是深度学习？它与机器学习的关系是什么？
回答: 深度学习是一种机器学习的技术，它通过模拟人脑神经网络的结构和功能来实现对数据的学习与预测。深度学习是机器学习的一个子领域，专注于使用多层神经网络（即'深度'结构）来处理复杂的数据模式。机器学习则是更广的概念，包含各种算法和技术，使计算机能够从数据中学习并做出预测或决策。

置信度: 0.919
推理方法: LLM驱动推理（大模型主体 + 图谱知识库）
推理过程:
  1. 步骤1：分析问题，明确用户需要了解'深度学习'的定义及其与'机器学习'的关系
  2. 步骤2：查找证据，从知识图谱中获取'深度学习'与'机器学习'的包含关系
  3. 步骤3：推理分析，结合证据说明深度学习属于机器学习的一个分支
  4. 步骤4：得出结论，给出完整定义和关系说明

📚 信息来源: 深度学习 --是--> 机器学习的技术, 机器学习 --是--> 人工智能的子领域
处理时间: 10.16秒
```

### 多模式推理对比
```
问题: 什么是深度学习？它与机器学习的关系是什么？

🔹 纯图算法:
  推理方法: graph_algorithm
  置信度: 0.600
  处理时间: 0.00秒
  回答: 推理链: 深度学习 → 机器学习的技术 (关系: 是)

🔹 混合推理:
  推理方法: 混合推理（图算法 + LLM语义理解）
  置信度: 0.940
  处理时间: 5.01秒
  回答: 推理链: 深度学习 → 机器学习的技术 (关系: 是)

💡 深度分析：深度学习是一种机器学习的技术，它通过模拟人脑处理数据的方式...

🔹 LLM驱动:
  推理方法: LLM驱动推理（大模型主体 + 图谱知识库）
  置信度: 0.919
  处理时间: 10.16秒
  回答: 深度学习是一种机器学习的技术，它通过模拟人脑神经网络的结构和功能...
```

## 🧠 推理引擎架构

### LLM驱动推理流程
```
用户查询 → 意图分析 → 搜索计划生成 → 图谱检索 → 证据整合 → LLM推理 → 答案生成
```

### 三种推理模式对比

| 特性 | 纯图算法 | 混合推理 | LLM驱动 |
|------|----------|----------|----------|
| 主体 | 图算法 | 图算法+LLM | 大模型 |
| 速度 | 极快 | 中等 | 较慢 |
| 质量 | 基础 | 高 | 最高 |
| 理解能力 | 有限 | 良好 | 优秀 |
| 推理深度 | 浅层 | 中等 | 深度 |
| 适用场景 | 快速查询 | 平衡性能 | 复杂分析 |

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
