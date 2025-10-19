# KQuest 使用指南

## 快速开始

### 1. 环境配置

KQuest 优先使用配置文件中的设置，只需要设置 API Key：

```bash
# 设置 ModelScope API Key（必需）
export OPENAI_API_KEY=your_modelscope_token

# 其他配置将从 config/config.yaml 文件读取
```

**重要说明**：
- 系统始终使用 `config/config.yaml` 文件中的模型配置
- 环境变量仅用于更新 API Key
- 不建议通过环境变量覆盖模型、URL 等配置

### 2. 基本使用

#### 知识抽取
```bash
# 从 Markdown 文件抽取知识图谱
kquest extract --input examples/sample_text.md --output output/kg.json

# 从文本文件抽取知识图谱
kquest extract --input examples/sample_text.txt --output output/kg.json

# 指定输出格式
kquest extract --input examples/sample_text.md --output output/kg.rdf --format rdf
```

#### 知识问答
```bash
# 基于知识图谱回答问题
kquest query --kg output/kg.json --question "什么是人工智能？"

# 交互式问答模式
kquest query --kg output/kg.json --interactive
```

### 3. 配置文件

配置文件位于 `config/config.yaml`，主要配置项：

```yaml
openai:
  api_key: "your_api_key"
  base_url: "https://api-inference.modelscope.cn/v1"
  model: "Qwen/Qwen2.5-32B-Instruct"
  temperature: 0.1
  max_tokens: 8000

extraction:
  chunk_size: 2000
  chunk_overlap: 200
  max_chunks_per_request: 5
  min_confidence: 0.5

reasoning:
  max_reasoning_depth: 3
  max_triples_per_query: 20
  similarity_threshold: 0.7
```

## 常见问题

### Q: 模型不存在错误
**错误**: `Error code: 400 - {'error': {'code': '1211', 'message': '模型不存在，请检查模型代码。'}}`

**解决方案**:
1. 检查环境变量设置：
   ```bash
   env | grep OPENAI
   ```
2. 确保 `OPENAI_BASE_URL` 设置为 `https://api-inference.modelscope.cn/v1`
3. 清除冲突的 `OPENAI_API_BASE` 变量

### Q: 认证失败
**错误**: `Error code: 401 - {'errors': {'message': 'Authentication failed...'}}`

**解决方案**:
1. 检查 API Key 是否正确
2. 确认 API Key 有效且未过期
3. 检查网络连接

### Q: 处理大文档超时
**解决方案**:
1. 调整配置文件中的 `chunk_size` 参数
2. 减少 `max_chunks_per_request` 值
3. 增加 `timeout` 设置

## 高级用法

### 批量处理
```bash
# 处理多个文件
for file in examples/*.md; do
    kquest extract --input "$file" --output "output/$(basename "$file" .md)_kg.json"
done
```

### 格式转换
```bash
# 转换为不同格式
kquest convert --input output/kg.json --output output/kg.rdf --format rdf
kquest convert --input output/kg.json --output output/kg.ttl --format ttl
```

### 自定义提示词
编辑 `config/prompts.yaml` 文件来自定义抽取和推理的提示词。

## 性能优化

1. **并发处理**: 系统支持并发处理多个文档块
2. **缓存机制**: 相同内容的处理结果会被缓存
3. **增量更新**: 支持对现有知识图谱的增量更新

## 故障排除

### 检查系统状态
```bash
# 检查配置
python -c "from src.kquest.config import get_config; config = get_config(); print(config.openai.base_url)"

# 测试 API 连接
kquest test --api
```

### 日志查看
```bash
# 查看详细日志
tail -f logs/kquest.log
```

## 支持的模型

目前支持的模型包括：
- Qwen/Qwen2.5-32B-Instruct (推荐)
- Qwen/Qwen2.5-72B-Instruct
- 其他兼容 OpenAI API 的模型

## 技术支持

如遇到问题，请：
1. 检查日志文件
2. 确认配置正确
3. 查看本文档的故障排除部分
4. 提交 Issue 到项目仓库
