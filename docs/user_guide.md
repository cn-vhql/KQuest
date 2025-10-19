# KQuest 用户指南

## 目录

1. [快速开始](#快速开始)
2. [安装配置](#安装配置)
3. [基本使用](#基本使用)
4. [命令行接口](#命令行接口)
5. [Python API](#python-api)
6. [配置说明](#配置说明)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)

## 快速开始

### 1. 安装

```bash
# 克隆项目
git clone <repository-url>
cd KQuest

# 安装依赖
pip install -e .

# 或安装开发依赖
pip install -e ".[dev]"
```

### 2. 配置

```bash
# 复制配置文件模板
cp config/config.yaml.example config/config.yaml

# 编辑配置文件，设置OpenAI API密钥
vim config/config.yaml
```

### 3. 第一次使用

```bash
# 从文本文件抽取知识图谱
kquest extract --input examples/sample_text.md --output output/kg.json

# 基于知识图谱回答问题
kquest query --kg output/kg.json --question "什么是人工智能？"

# 交互式问答
kquest query --kg output/kg.json --interactive
```

## 安装配置

### 系统要求

- Python 3.11+
- OpenAI API Key

### 环境变量配置

除了配置文件，你也可以使用环境变量：

```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export OPENAI_MODEL="gpt-3.5-turbo"  # 可选
export DEBUG="true"  # 可选
```

### 配置文件详解

配置文件位于 `config/config.yaml`，主要包含以下部分：

#### OpenAI 配置
```yaml
openai:
  api_key: "your-openai-api-key"  # 必填
  base_url: null  # 可选，自定义API端点
  model: "gpt-3.5-turbo"  # 使用的模型
  temperature: 0.1  # 温度参数
  max_tokens: 2000  # 最大token数
```

#### 抽取配置
```yaml
extraction:
  chunk_size: 2000  # 文本分块大小
  chunk_overlap: 200  # 分块重叠
  max_chunks_per_request: 5  # 每次请求的最大分块数
  min_confidence: 0.5  # 最小置信度阈值
  enable_filtering: true  # 是否启用结果过滤
```

#### 推理配置
```yaml
reasoning:
  max_reasoning_depth: 3  # 最大推理深度
  max_triples_per_query: 20  # 每次查询最大三元组数
  enable_fuzzy_matching: true  # 是否启用模糊匹配
  similarity_threshold: 0.7  # 相似度阈值
```

## 基本使用

### 知识抽取

从文本文件中抽取知识图谱：

```bash
# 基本用法
kquest extract -i document.md -o knowledge.json

# 指定输出格式
kquest extract -i document.md -o knowledge.rdf -f rdf

# 启用压缩
kquest extract -i document.md -o knowledge.json.gz --compress

# 指定语言和领域
kquest extract -i document.md -o knowledge.json -l zh -d "计算机科学"
```

### 知识问答

基于知识图谱回答问题：

```bash
# 单次查询
kquest query --kg knowledge.json --question "什么是机器学习？"

# 交互式查询
kquest query --kg knowledge.json --interactive

# 限制返回结果数量
kquest query --kg knowledge.json --question "AI的应用" --max-results 3
```

### 知识图谱管理

```bash
# 查看知识图谱信息
kquest info --kg knowledge.json

# 列出所有知识图谱文件
kquest list

# 转换文件格式
kquest convert knowledge.json knowledge.rdf --to-format rdf

# 删除知识图谱文件
kquest delete knowledge.json --confirm
```

## 命令行接口

### extract 命令

从文本文件抽取知识图谱。

```bash
kquest extract [OPTIONS]
```

**选项：**
- `-i, --input`: 输入文件路径（必需）
- `-o, --output`: 输出文件路径（必需）
- `-f, --format`: 输出格式（rdf|json|jsonld|csv|ttl）
- `--compress`: 压缩输出文件
- `-l, --language`: 文档语言
- `-d, --domain`: 专业领域

**示例：**
```bash
kquest extract -i research_paper.md -o paper_kg.rdf -f rdf -l en -d "machine_learning"
```

### query 命令

基于知识图谱回答问题。

```bash
kquest query [OPTIONS]
```

**选项：**
- `--kg, --knowledge-graph`: 知识图谱文件路径（必需）
- `-q, --question`: 要查询的问题
- `-i, --interactive`: 交互式问答模式
- `--max-results`: 最大显示结果数

**示例：**
```bash
# 单次查询
kquest query --kg ai_knowledge.json --question "深度学习的原理是什么？"

# 交互式模式
kquest query --kg ai_knowledge.json --interactive
```

### info 命令

显示知识图谱统计信息。

```bash
kquest info [OPTIONS]
```

**选项：**
- `--kg, --knowledge-graph`: 知识图谱文件路径（必需）
- `-f, --format`: 显示格式（table|json|summary）

**示例：**
```bash
kquest info --kg ai_knowledge.json --format table
```

### list 命令

列出已保存的知识图谱文件。

```bash
kquest list [OPTIONS]
```

**选项：**
- `-d, --directory`: 目录路径
- `-f, --format`: 显示格式（table|json）

### convert 命令

转换知识图谱文件格式。

```bash
kquest convert [OPTIONS] INPUT_FILE OUTPUT_FILE
```

**选项：**
- `--from-format`: 输入格式
- `--to-format`: 输出格式

## Python API

### 基本用法

```python
from kquest import KnowledgeExtractor, KnowledgeReasoner, KnowledgeStorage, Config

# 加载配置
config = Config.from_yaml("config/config.yaml")

# 创建组件
extractor = KnowledgeExtractor(config)
reasoner = KnowledgeReasoner(config)
storage = KnowledgeStorage(config)

# 知识抽取
result = extractor.extract_from_file_sync("document.md")
if result.success:
    knowledge_graph = result.knowledge_graph
    
    # 保存知识图谱
    storage.save_knowledge_graph(knowledge_graph, "output.json")
    
    # 知识问答
    query_result = reasoner.query_sync("什么是人工智能？", knowledge_graph)
    print(f"回答: {query_result.answer}")
    print(f"置信度: {query_result.confidence}")
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
        query_result = await reasoner.query(
            "机器学习有什么应用？", 
            result.knowledge_graph
        )
        print(query_result.answer)

# 运行异步函数
asyncio.run(main())
```

### 手动创建知识图谱

```python
from kquest import KnowledgeGraph, KnowledgeTriple, TripleType

# 创建三元组
triples = [
    KnowledgeTriple(
        subject="Python",
        predicate="是",
        object="编程语言",
        triple_type=TripleType.CLASS_RELATION,
        confidence=1.0
    ),
    KnowledgeTriple(
        subject="Python",
        predicate="适用于",
        object="数据科学",
        triple_type=TripleType.ENTITY_RELATION,
        confidence=0.9
    )
]

# 创建知识图谱
kg = KnowledgeGraph(triples=triples)

# 查询统计信息
stats = kg.get_statistics()
print(f"总三元组数: {stats['total_triples']}")
```

## 配置说明

### 抽取参数调优

#### chunk_size
- **说明**: 文本分块的大小
- **建议**: 
  - 短文本: 1000-1500
  - 长文档: 2000-3000
  - API限制: 考虑模型的token限制

#### min_confidence
- **说明**: 最小置信度阈值
- **建议**:
  - 高质量要求: 0.7-0.8
  - 一般用途: 0.5-0.6
  - 探索性分析: 0.3-0.4

#### temperature
- **说明**: 生成随机性控制
- **建议**:
  - 事实抽取: 0.1-0.3
  - 创造性任务: 0.5-0.7
  - 推理任务: 0.2-0.4

### 推理参数调优

#### similarity_threshold
- **说明**: 模糊匹配的相似度阈值
- **建议**:
  - 精确匹配: 0.8-0.9
  - 一般匹配: 0.6-0.8
  - 宽松匹配: 0.4-0.6

#### max_triples_per_query
- **说明**: 每次查询使用的最大三元组数
- **建议**:
  - 简单问题: 5-10
  - 复杂问题: 15-25
  - API成本考虑: 限制数量

## 最佳实践

### 1. 文本预处理

```python
# 清理文本
def preprocess_text(text):
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符（保留中文、英文、标点）
    text = re.sub(r'[^\w\s\u4e00-\u9fff。，！？；：""''（）【】]', '', text)
    
    return text.strip()

# 使用清理后的文本进行抽取
clean_text = preprocess_text(raw_text)
result = extractor.extract_from_text(clean_text)
```

### 2. 批量处理

```python
from pathlib import Path

async def batch_extract(directory, output_dir):
    extractor = KnowledgeExtractor()
    
    for file_path in Path(directory).glob("*.md"):
        print(f"处理文件: {file_path}")
        
        result = await extractor.extract_from_file(file_path)
        
        if result.success:
            output_file = Path(output_dir) / f"{file_path.stem}.json"
            storage.save_knowledge_graph(result.knowledge_graph, output_file)
            print(f"已保存: {output_file}")

# 运行批量处理
asyncio.run(batch_extract("documents/", "output/"))
```

### 3. 质量控制

```python
def filter_high_quality_triples(knowledge_graph, min_confidence=0.8):
    """过滤高质量三元组"""
    filtered_triples = [
        triple for triple in knowledge_graph.triples
        if triple.confidence >= min_confidence
    ]
    
    return KnowledgeGraph(triples=filtered_triples)

def remove_duplicates(knowledge_graph):
    """移除重复的三元组"""
    seen = set()
    unique_triples = []
    
    for triple in knowledge_graph.triples:
        key = (triple.subject, triple.predicate, triple.object)
        if key not in seen:
            seen.add(key)
            unique_triples.append(triple)
    
    return KnowledgeGraph(triples=unique_triples)
```

### 4. 错误处理

```python
import logging
from kquest import KnowledgeExtractor

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_extract(file_path):
    try:
        extractor = KnowledgeExtractor()
        result = await extractor.extract_from_file(file_path)
        
        if not result.success:
            logger.error(f"抽取失败: {result.error_message}")
            return None
            
        return result.knowledge_graph
        
    except Exception as e:
        logger.error(f"处理文件时发生错误: {e}")
        return None
```

### 5. 性能优化

```python
# 使用缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_similarity(text1, text2):
    """缓存的相似度计算"""
    return calculate_similarity(text1, text2)

# 限制并发请求数
import asyncio

async def rate_limited_extract(extractor, files, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_with_limit(file_path):
        async with semaphore:
            return await extractor.extract_from_file(file_path)
    
    tasks = [extract_with_limit(file) for file in files]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## 常见问题

### Q1: 如何处理大文件？

**A**: 对于大文件，建议：
1. 调整 `chunk_size` 参数（建议 2000-3000）
2. 减少 `max_chunks_per_request` 以避免API限制
3. 考虑将文件分割成多个小文件分别处理

### Q2: 抽取结果质量不高怎么办？

**A**: 可以尝试：
1. 提高 `min_confidence` 阈值
2. 降低 `temperature` 参数（0.1-0.2）
3. 启用 `enable_filtering`
4. 预处理文本，移除噪声
5. 指定正确的 `domain` 参数

### Q3: API调用失败如何处理？

**A**: 检查以下几点：
1. API密钥是否正确
2. 网络连接是否正常
3. 是否超出API配额
4. 增加 `max_retries` 和 `retry_delay`
5. 检查 `timeout` 设置

### Q4: 如何处理特定领域的文本？

**A**: 
1. 设置 `domain` 参数指定专业领域
2. 使用自定义提示词模板
3. 预训练领域特定的术语
4. 调整 `min_confidence` 阈值

### Q5: 知识图谱文件太大怎么办？

**A**: 
1. 使用 `compress` 选项压缩文件
2. 过滤低质量三元组
3. 按主题分割知识图谱
4. 使用更高效的格式（如Turtle）

### Q6: 如何提高问答准确性？

**A**: 
1. 增加 `max_triples_per_query`
2. 启用 `enable_fuzzy_matching`
3. 调整 `similarity_threshold`
4. 使用更好的提示词模板
5. 提高输入知识图谱的质量

### Q7: 支持哪些文件格式？

**A**: 输入支持：
- Markdown (.md)
- 纯文本 (.txt)
- 其他文本格式

输出支持：
- JSON (.json)
- RDF/XML (.rdf, .xml)
- JSON-LD (.jsonld)
- CSV (.csv)
- Turtle (.ttl)

### Q8: 如何自定义提示词？

**A**: 编辑 `config/prompts.yaml` 文件，修改相应的提示词模板。重启程序后生效。

---

## 更多帮助

如果遇到其他问题，请：
1. 查看项目文档
2. 检查日志文件
3. 启用调试模式 (`--debug`)
4. 提交Issue到项目仓库
