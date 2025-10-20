"""Streamlit可视化界面模块"""

import streamlit as st
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from kquest.config import get_config, Config
from kquest.extractor import KnowledgeExtractor
from kquest.storage import KnowledgeStorage
from kquest.models import KnowledgeGraph, KnowledgeTriple, QueryResult
from kquest.reasoning import KnowledgeReasoner

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_session_state():
    """初始化会话状态"""
    if 'config' not in st.session_state:
        st.session_state.config = get_config()
    if 'extractor' not in st.session_state:
        st.session_state.extractor = None
    if 'reasoner' not in st.session_state:
        st.session_state.reasoner = None
    if 'knowledge_graph' not in st.session_state:
        st.session_state.knowledge_graph = None
    if 'extraction_result' not in st.session_state:
        st.session_state.extraction_result = None
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []

def init_services():
    """初始化服务"""
    try:
        if not st.session_state.config.openai.api_key:
            st.error("请在配置页面设置OpenAI API Key")
            return False

        st.session_state.extractor = KnowledgeExtractor(st.session_state.config)
        st.session_state.reasoner = KnowledgeReasoner(st.session_state.config)
        return True
    except Exception as e:
        st.error(f"初始化服务失败: {str(e)}")
        return False

def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.title("KQuest 知识图谱系统")

    page = st.sidebar.selectbox(
        "选择功能页面",
        ["配置管理", "知识抽取", "智能问答", "图谱可视化", "系统信息"]
    )

    # 显示状态信息
    if st.session_state.config.openai.api_key:
        st.sidebar.success("✓ API Key已配置")
    else:
        st.sidebar.warning("⚠️ 需要配置API Key")

    if st.session_state.knowledge_graph:
        st.sidebar.info(f"📊 当前图谱: {len(st.session_state.knowledge_graph.triples)} 个三元组")

    return page

def render_config_page():
    """渲染配置管理页面"""
    st.header("⚙️ 配置管理")

    # OpenAI配置
    st.subheader("OpenAI API 配置")

    with st.form("openai_config"):
        api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.config.openai.api_key or "",
            help="OpenAI API Key"
        )

        base_url = st.text_input(
            "Base URL (可选)",
            value=st.session_state.config.openai.base_url or "",
            help="自定义API端点，留空使用默认"
        )

        model = st.selectbox(
            "模型选择",
            options=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            index=0 if st.session_state.config.openai.model == "gpt-3.5-turbo" else 0
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.config.openai.temperature,
            step=0.1
        )

        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=8000,
            value=st.session_state.config.openai.max_tokens or 2000
        )

        submitted = st.form_submit_button("保存配置")

        if submitted:
            if not api_key:
                st.error("API Key不能为空")
                return

            # 更新配置
            st.session_state.config.openai.update_api_key(api_key)
            st.session_state.config.openai.base_url = base_url if base_url else None
            st.session_state.config.openai.model = model
            st.session_state.config.openai.temperature = temperature
            st.session_state.config.openai.max_tokens = max_tokens

            # 重新初始化服务
            if init_services():
                st.success("配置保存成功！")
            else:
                st.error("配置保存失败，请检查API Key是否正确")

    # 抽取配置
    st.subheader("知识抽取配置")

    with st.form("extraction_config"):
        chunk_size = st.number_input(
            "文档分块大小",
            min_value=500,
            max_value=10000,
            value=st.session_state.config.extraction.chunk_size,
            step=100
        )

        chunk_overlap = st.number_input(
            "分块重叠大小",
            min_value=0,
            max_value=1000,
            value=st.session_state.config.extraction.chunk_overlap,
            step=50
        )

        confidence_threshold = st.slider(
            "置信度阈值",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.config.extraction.min_confidence,
            step=0.1
        )

        submitted = st.form_submit_button("更新抽取配置")

        if submitted:
            st.session_state.config.extraction.chunk_size = chunk_size
            st.session_state.config.extraction.chunk_overlap = chunk_overlap
            st.session_state.config.extraction.min_confidence = confidence_threshold
            st.success("抽取配置更新成功！")

def render_extraction_page():
    """渲染知识抽取页面"""
    st.header("📄 知识抽取")

    if not st.session_state.extractor:
        st.error("请先在配置页面设置API Key")
        return

    # 文件上传
    st.subheader("上传文档")
    uploaded_file = st.file_uploader(
        "选择要抽取的文档",
        type=['txt', 'md', 'json'],
        help="支持TXT、Markdown、JSON格式"
    )

    if uploaded_file:
        st.info(f"已选择文件: {uploaded_file.name}")

        # 显示文件内容预览
        content = uploaded_file.read().decode('utf-8')
        with st.expander("文件内容预览"):
            st.text_area("内容", content, height=200)

        # 抽取参数
        st.subheader("抽取参数")
        st.info("抽取将使用配置页面中的参数设置")

        # 开始抽取
        if st.button("🚀 开始抽取", type="primary"):
            with st.spinner("正在抽取知识图谱..."):
                try:
                    # 重置文件指针
                    uploaded_file.seek(0)
                    temp_file_path = f"/tmp/{uploaded_file.name}"

                    # 保存临时文件
                    with open(temp_file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    # 执行抽取
                    result = st.session_state.extractor.extract_from_file_sync(
                        temp_file_path
                    )

                    if result.success:
                        st.session_state.knowledge_graph = result.knowledge_graph
                        st.session_state.extraction_result = result

                        st.success(f"抽取完成！成功抽取 {result.extracted_triples} 个三元组")

                        # 显示抽取结果
                        render_extraction_result(result)
                    else:
                        st.error(f"抽取失败: {result.error_message}")

                    # 清理临时文件
                    os.remove(temp_file_path)

                except Exception as e:
                    st.error(f"抽取过程中出错: {str(e)}")
                    logger.error(f"Extraction error: {e}")

def render_extraction_result(result):
    """渲染抽取结果"""
    st.subheader("📊 抽取结果")

    # 统计信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("三元组数量", result.extracted_triples)

    with col2:
        st.metric("处理时间", f"{result.processing_time:.2f}s")

    with col3:
        stats = result.knowledge_graph.get_statistics()
        st.metric("唯一实体", stats['unique_subjects'] + stats['unique_objects'])

    with col4:
        st.metric("关系类型", stats['unique_predicates'])

    # 三元组列表
    st.subheader("抽取的三元组")

    # 过滤选项
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox(
            "过滤类型",
            ["全部", "高置信度", "中置信度", "低置信度"]
        )
    with col2:
        search_term = st.text_input("搜索关键词")

    # 过滤和搜索三元组
    filtered_triples = []
    for triple in result.knowledge_graph.triples:
        # 置信度过滤
        if filter_type == "高置信度" and triple.confidence < 0.8:
            continue
        elif filter_type == "中置信度" and not (0.5 <= triple.confidence < 0.8):
            continue
        elif filter_type == "低置信度" and triple.confidence >= 0.5:
            continue

        # 关键词搜索
        if search_term:
            if (search_term.lower() not in triple.subject.lower() and
                search_term.lower() not in triple.predicate.lower() and
                search_term.lower() not in triple.object.lower()):
                continue

        filtered_triples.append(triple)

    # 显示三元组
    if filtered_triples:
        for i, triple in enumerate(filtered_triples):
            with st.expander(f"{triple.subject} --{triple.predicate}--> {triple.object} (置信度: {triple.confidence:.2f})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**类型**: {triple.triple_type.value}")
                    st.write(f"**置信度**: {triple.confidence:.2f}")
                    st.write(f"**置信度级别**: {triple.confidence_level.value}")
                with col2:
                    if triple.source:
                        st.write(f"**来源**: {triple.source[:100]}...")
                    if triple.metadata:
                        st.write("**元数据**:")
                        st.json(triple.metadata)
    else:
        st.info("没有找到匹配的三元组")

def render_qa_page():
    """渲染智能问答页面"""
    st.header("🤖 智能问答")

    if not st.session_state.knowledge_graph:
        st.warning("请先在知识抽取页面创建知识图谱")
        return

    if not st.session_state.reasoner:
        st.error("请先在配置页面设置API Key")
        return

    # 问答输入
    st.subheader("提出问题")

    question = st.text_input(
        "请输入您的问题",
        placeholder="例如：什么是人工智能？",
        key="question_input"
    )

    # 推理模式选择
    st.subheader("🧠 推理模式")
    col1, col2, col3 = st.columns(3)

    reasoning_modes = {
        "graph": {
            "name": "纯图算法",
            "description": "基于传统图算法的快速推理",
            "icon": "📊",
            "speed": "极快",
            "quality": "基础"
        },
        "hybrid": {
            "name": "混合推理",
            "description": "结合图算法与LLM语义理解",
            "icon": "🔗",
            "speed": "中等",
            "quality": "高"
        },
        "llm_driven": {
            "name": "LLM驱动",
            "description": "大模型为主体的智能推理",
            "icon": "🚀",
            "speed": "较慢",
            "quality": "最高"
        }
    }

    selected_mode = None
    for i, (mode, info) in enumerate(reasoning_modes.items()):
        with [col1, col2, col3][i]:
            if st.button(
                f"{info['icon']} {info['name']}",
                help=f"{info['description']}\\n速度: {info['speed']} | 质量: {info['quality']}",
                use_container_width=True,
                type="primary" if st.session_state.get('selected_reasoning_mode') == mode else "secondary"
            ):
                selected_mode = mode

    # 如果没有选择，使用默认或之前的选择
    if selected_mode is None:
        selected_mode = st.session_state.get('selected_reasoning_mode', 'graph')

    st.session_state.selected_reasoning_mode = selected_mode

    # 显示当前选择和模式对比
    current_mode_info = reasoning_modes[selected_mode]
    st.info(f"当前模式: {current_mode_info['icon']} **{current_mode_info['name']}** - {current_mode_info['description']}")

    # 模式对比表格
    with st.expander("📊 推理模式对比"):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**模式**")
            for mode, info in reasoning_modes.items():
                st.markdown(f"{info['icon']} {info['name']}")

        with col2:
            st.markdown("**速度**")
            for mode, info in reasoning_modes.items():
                if info['speed'] == '极快':
                    st.markdown("⚡ 极快")
                elif info['speed'] == '中等':
                    st.markdown("🚶 中等")
                else:
                    st.markdown("🐌 较慢")

        with col3:
            st.markdown("**质量**")
            for mode, info in reasoning_modes.items():
                if info['quality'] == '最高':
                    st.markdown("⭐⭐⭐ 最高")
                elif info['quality'] == '高':
                    st.markdown("⭐⭐ 高")
                else:
                    st.markdown("⭐ 基础")

        with col4:
            st.markdown("**适用场景**")
            st.markdown("• 快速查询")
            st.markdown("• 平衡性能")
            st.markdown("• 复杂分析")

    # 创建对应模式的推理器
    if (st.session_state.reasoner is None or
        st.session_state.get('current_reasoning_mode') != selected_mode):

        try:
            st.session_state.reasoner = KnowledgeReasoner(
                config=st.session_state.config,
                knowledge_graph=st.session_state.knowledge_graph,
                reasoning_mode=selected_mode
            )
            st.session_state.current_reasoning_mode = selected_mode
            st.success(f"已切换到 {current_mode_info['name']} 模式")
        except Exception as e:
            st.error(f"切换推理模式失败: {str(e)}")
            return

    if st.button("💡 提问", type="primary") and question:
        with st.spinner("正在思考..."):
            try:
                # 执行问答
                result = st.session_state.reasoner.query_sync(
                    question,
                    st.session_state.knowledge_graph
                )

                # 添加推理模式信息到结果中
                result.metadata['reasoning_mode'] = selected_mode
                result.metadata['reasoning_mode_name'] = current_mode_info['name']
                result.metadata['reasoning_mode_icon'] = current_mode_info['icon']

                # 添加到历史记录
                st.session_state.query_history.append(result)

                # 显示结果
                render_qa_result(result, current_mode_info)

            except Exception as e:
                st.error(f"问答过程中出错: {str(e)}")
                logger.error(f"QA error: {e}")

    # 历史记录
    if st.session_state.query_history:
        st.subheader("💬 问答历史")

        for i, result in enumerate(reversed(st.session_state.query_history[-5:])):
            # 获取推理模式信息
            mode_icon = result.metadata.get('reasoning_mode_icon', '❓')
            mode_name = result.metadata.get('reasoning_mode_name', '未知模式')

            with st.expander(f"Q: {result.question} ({mode_icon} {mode_name}, 置信度: {result.confidence:.2f})"):
                st.write(f"**A**: {result.answer}")

                # 显示推理方法
                if result.metadata.get('method'):
                    st.write(f"🔧 **推理方法**: {result.metadata['method']}")

                if result.reasoning_path:
                    st.write("**推理过程**:")
                    for step in result.reasoning_path:
                        st.write(f"- {step}")

                if result.source_triples:
                    st.write("**来源三元组**:")
                    for triple in result.source_triples:
                        st.write(f"- {triple}")

def render_qa_result(result, mode_info=None):
    """渲染问答结果"""
    # 显示推理模式
    if mode_info and result.metadata.get('reasoning_mode'):
        st.success(f"{mode_info['icon']} 使用 **{mode_info['name']}** 模式回答")

    st.subheader("💡 回答")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(result.answer)
    with col2:
        st.metric("置信度", f"{result.confidence:.2f}")
    with col3:
        if mode_info:
            st.metric("模式", mode_info['name'])

    # 显示推理方法信息
    if result.metadata.get('method'):
        st.info(f"🔧 推理方法: {result.metadata['method']}")

    # 推理路径
    if result.reasoning_path:
        st.subheader("🔍 推理过程")
        for i, step in enumerate(result.reasoning_path, 1):
            st.write(f"{i}. {step}")

    # 来源三元组
    if result.source_triples:
        st.subheader("📚 相关知识")
        for triple in result.source_triples:
            st.write(f"- {triple}")

    # 显示额外元数据
    extra_metadata = {k: v for k, v in result.metadata.items()
                     if k not in ['reasoning_mode', 'reasoning_mode_name', 'reasoning_mode_icon', 'method']}
    if extra_metadata:
        st.subheader("ℹ️ 附加信息")
        for key, value in extra_metadata.items():
            st.write(f"- **{key}**: {value}")

def render_visualization_page():
    """渲染图谱可视化页面"""
    st.header("🎨 知识图谱可视化")

    if not st.session_state.knowledge_graph:
        st.warning("请先在知识抽取页面创建知识图谱")
        return

    kg = st.session_state.knowledge_graph

    # 图谱统计
    st.subheader("📊 图谱统计")
    stats = kg.get_statistics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("三元组总数", stats['total_triples'])
    with col2:
        st.metric("唯一主语", stats['unique_subjects'])
    with col3:
        st.metric("唯一宾语", stats['unique_objects'])
    with col4:
        st.metric("唯一关系", stats['unique_predicates'])

    # 三元组类型分布
    st.subheader("📈 三元组类型分布")

    try:
        import matplotlib.pyplot as plt
        import pandas as pd

        # 三元组类型分布饼图
        triple_types = stats['triple_types']
        if any(triple_types.values()):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**三元组类型分布**")
                # 创建饼图
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                labels = [k for k, v in triple_types.items() if v > 0]
                sizes = [v for k, v in triple_types.items() if v > 0]
                ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
                ax1.set_title('三元组类型分布')
                st.pyplot(fig1)
                plt.close()

            with col2:
                st.write("**置信度分布**")
                # 创建柱状图
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                confidence_dist = stats['confidence_distribution']
                levels = list(confidence_dist.keys())
                counts = list(confidence_dist.values())
                ax2.bar(levels, counts)
                ax2.set_title('置信度分布')
                ax2.set_ylabel('数量')
                st.pyplot(fig2)
                plt.close()
        else:
            st.info("暂无数据")
    except ImportError:
        st.warning("可视化功能需要安装 matplotlib 库。请运行: pip install matplotlib")
        # 显示简单的文本统计
        st.write("**三元组类型分布**:")
        for triple_type, count in stats['triple_types'].items():
            if count > 0:
                st.write(f"- {triple_type}: {count}")

        st.write("**置信度分布**:")
        for level, count in stats['confidence_distribution'].items():
            if count > 0:
                st.write(f"- {level}: {count}")

    # 实体关系网络
    st.subheader("🕸️ 实体关系网络")

    try:
        # 创建简单的网络图
        import networkx as nx
        import matplotlib.pyplot as plt

        G = nx.DiGraph()

        # 添加节点和边
        for triple in kg.triples[:50]:  # 限制显示数量以提高性能
            G.add_edge(triple.subject, triple.object, label=triple.predicate)

        if G.number_of_nodes() > 0:
            fig, ax = plt.subplots(figsize=(12, 8))
            pos = nx.spring_layout(G, k=1, iterations=50)

            # 绘制节点
            nx.draw_networkx_nodes(G, pos, node_color='lightblue',
                                  node_size=500, alpha=0.7, ax=ax)

            # 绘制边
            nx.draw_networkx_edges(G, pos, edge_color='gray',
                                  arrows=True, arrowsize=20, alpha=0.5, ax=ax)

            # 绘制标签
            nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)

            ax.set_title("知识图谱网络结构 (显示前50个三元组)")
            ax.axis('off')
            st.pyplot(fig)
            plt.close()
        else:
            st.info("图谱为空")
    except ImportError:
        st.warning("网络可视化功能需要安装 networkx 和 matplotlib 库。")
        # 显示简单的文本关系
        st.write("**实体关系**:")
        for i, triple in enumerate(kg.triples[:10]):  # 只显示前10个
            st.write(f"{i+1}. {triple.subject} --{triple.predicate}--> {triple.object}")
        if len(kg.triples) > 10:
            st.write(f"... 还有 {len(kg.triples) - 10} 个三元组")

    # 关系列表
    st.subheader("🔗 关系列表")

    # 按关系统计
    predicate_counts = {}
    for triple in kg.triples:
        predicate_counts[triple.predicate] = predicate_counts.get(triple.predicate, 0) + 1

    if predicate_counts:
        try:
            import pandas as pd
            pred_df = pd.DataFrame([
                {'关系': pred, '数量': count}
                for pred, count in sorted(predicate_counts.items(), key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(pred_df, use_container_width=True)
        except ImportError:
            st.warning("数据表格功能需要安装 pandas 库。")
            # 显示简单的文本列表
            st.write("**关系统计**:")
            for pred, count in sorted(predicate_counts.items(), key=lambda x: x[1], reverse=True):
                st.write(f"- {pred}: {count}")
    else:
        st.info("暂无关系数据")

def render_info_page():
    """渲染系统信息页面"""
    st.header("ℹ️ 系统信息")

    # 系统配置
    st.subheader("⚙️ 当前配置")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**OpenAI 配置**")
        st.write(f"- 模型: {st.session_state.config.openai.model}")
        st.write(f"- Temperature: {st.session_state.config.openai.temperature}")
        st.write(f"- Max Tokens: {st.session_state.config.openai.max_tokens}")
        if st.session_state.config.openai.base_url:
            st.write(f"- Base URL: {st.session_state.config.openai.base_url}")

    with col2:
        st.write("**抽取配置**")
        st.write(f"- 分块大小: {st.session_state.config.extraction.chunk_size}")
        st.write(f"- 分块重叠: {st.session_state.config.extraction.chunk_overlap}")
        st.write(f"- 置信度阈值: {st.session_state.config.extraction.min_confidence}")

    # 图谱信息
    if st.session_state.knowledge_graph:
        st.subheader("📊 当前图谱信息")

        stats = st.session_state.knowledge_graph.get_statistics()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("三元组总数", stats['total_triples'])
            st.metric("创建时间", st.session_state.knowledge_graph.created_at.strftime('%Y-%m-%d %H:%M:%S'))

        with col2:
            st.metric("更新时间", st.session_state.knowledge_graph.updated_at.strftime('%Y-%m-%d %H:%M:%S'))
            st.metric("元数据字段", len(st.session_state.knowledge_graph.metadata))

    # 使用说明
    st.subheader("📖 使用说明")

    st.markdown("""
    ### KQuest 知识图谱系统使用指南

    1. **配置管理**: 设置OpenAI API Key和相关参数
    2. **知识抽取**: 上传文档，自动抽取知识三元组
    3. **智能问答**: 基于抽取的知识图谱进行问答
    4. **图谱可视化**: 查看知识图谱的统计信息和网络结构

    ### 支持的文件格式
    - TXT: 纯文本文件
    - MD: Markdown格式文件
    - JSON: JSON格式文件

    ### 问答示例
    - "什么是人工智能？"
    - "X和Y有什么关系？"
    - "列出所有的Z属性"
    """)

def main():
    """主函数"""
    st.set_page_config(
        page_title="KQuest 知识图谱系统",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 初始化会话状态
    init_session_state()

    # 初始化服务
    if not st.session_state.extractor and st.session_state.config.openai.api_key:
        init_services()

    # 渲染侧边栏
    page = render_sidebar()

    # 根据选择渲染对应页面
    if page == "配置管理":
        render_config_page()
    elif page == "知识抽取":
        render_extraction_page()
    elif page == "智能问答":
        render_qa_page()
    elif page == "图谱可视化":
        render_visualization_page()
    elif page == "系统信息":
        render_info_page()

if __name__ == "__main__":
    main()