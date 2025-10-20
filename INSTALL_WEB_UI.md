# KQuest Web UI 安装指南

## 📦 环境要求

- Python 3.11+
- OpenAI API Key

## 🚀 快速安装

### 1. 安装基础依赖

```bash
# 克隆项目
git clone <repository-url>
cd KQuest

# 安装基础依赖
uv sync
```

### 2. 安装可视化依赖（可选）

如果您想要完整的可视化功能，请安装以下依赖：

```bash
# 安装可视化库
pip install matplotlib pandas networkx

# 或者使用 uv
uv add matplotlib pandas networkx
```

### 3. 配置API Key

```bash
# 设置环境变量
export OPENAI_API_KEY="your-openai-api-key-here"
```

或在Web UI的配置页面中设置。

## 🎯 启动Web UI

```bash
# 使用便捷脚本启动
python run_web.py

# 或直接使用streamlit
streamlit run src/kquest/web_ui.py
```

然后访问 http://localhost:8501

## 📋 功能说明

### 基础功能（无需额外依赖）
- ✅ 配置管理
- ✅ 文件上传和知识抽取
- ✅ 智能问答
- ✅ 系统信息查看

### 可视化功能（需要额外依赖）
- 📊 三元组类型分布图
- 📈 置信度分布图
- 🕸️ 知识图谱网络图
- 📋 关系统计表格

如果没有安装可视化依赖，Web UI会显示简化的文本版本。

## 🔧 故障排除

### 常见问题

#### 1. ModuleNotFoundError: No module named 'matplotlib'
```bash
pip install matplotlib
```

#### 2. ModuleNotFoundError: No module named 'pandas'
```bash
pip install pandas
```

#### 3. ModuleNotFoundError: No module named 'networkx'
```bash
pip install networkx
```

#### 4. API Key错误
- 在配置页面设置正确的OpenAI API Key
- 确认API账户有足够的余额

#### 5. 端口被占用
```bash
# 使用不同端口启动
streamlit run src/kquest/web_ui.py --server.port=8502
```

## 💡 使用建议

1. **首次使用**：建议先在配置页面设置API Key
2. **文档格式**：支持TXT、MD、JSON格式
3. **性能优化**：大文档建议分批处理
4. **浏览器**：推荐使用Chrome、Firefox等现代浏览器

## 🆘 获取帮助

如遇到问题，请：
1. 查看本文档的故障排除部分
2. 检查项目的GitHub Issues
3. 提交新的Issue

---

🎉 现在您可以通过图形界面轻松使用KQuest的所有功能！