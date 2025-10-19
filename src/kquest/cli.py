"""CLI命令行接口模块"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live

from .config import Config, get_config, load_config
from .extractor import KnowledgeExtractor
from .reasoning import KnowledgeReasoner
from .storage import KnowledgeStorage
from .models import TaskStatus, ProcessingStatus


# 全局控制台对象
console = Console()


def setup_logging(config: Config) -> None:
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        format=config.logging.format,
        filename=config.logging.file_path,
        filemode='a',
    )
    
    # 如果启用了控制台输出，创建控制台处理器
    if config.logging.console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.logging.level.upper()))
        console_handler.setFormatter(logging.Formatter(config.logging.format))
        logging.getLogger().addHandler(console_handler)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='配置文件路径')
@click.option('--debug', is_flag=True, help='启用调试模式')
@click.pass_context
def main(ctx, config: Optional[str], debug: bool):
    """KQuest - 知识图谱抽取与问答系统"""
    try:
        # 加载配置
        if config:
            ctx.obj = load_config(config)
        else:
            ctx.obj = get_config()
        
        # 覆盖调试模式
        if debug:
            ctx.obj.debug = True
            ctx.obj.logging.level = "DEBUG"
        
        # 设置日志
        setup_logging(ctx.obj)
        
        # 验证配置
        errors = ctx.obj.validate_config()
        if errors:
            console.print("[red]配置验证失败:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            sys.exit(1)
        
        if ctx.obj.debug:
            console.print(f"[green]✓[/green] 配置加载成功: {ctx.obj.project_name} v{ctx.obj.version}")
            
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True), help='输入文件路径')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(), help='输出文件路径')
@click.option('--format', '-f', type=click.Choice(['rdf', 'json', 'jsonld', 'csv', 'ttl']), help='输出格式')
@click.option('--compress', is_flag=True, help='压缩输出文件')
@click.option('--language', '-l', default='zh', help='文档语言')
@click.option('--domain', '-d', help='专业领域')
@click.pass_obj
def extract(config: Config, input_file: str, output_file: str, format: Optional[str], compress: bool, language: str, domain: Optional[str]):
    """从文本文件抽取知识图谱"""
    
    # 更新配置
    if format:
        config.storage.default_format = format
    config.extraction.language = language
    if domain:
        config.extraction.domain = domain
    
    # 创建组件
    extractor = KnowledgeExtractor(config)
    storage = KnowledgeStorage(config)
    
    # 创建任务状态
    task_status = TaskStatus(
        task_id=f"extract_{Path(input_file).stem}_{int(asyncio.get_event_loop().time())}",
        status=ProcessingStatus.PENDING
    )
    
    console.print(f"[blue]开始从文件抽取知识图谱:[/blue] {input_file}")
    
    try:
        # 使用进度条显示处理进度
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task_progress = progress.add_task("处理中...", total=100)
            
            def update_progress():
                if task_status.progress > 0:
                    progress.update(task_progress, completed=task_status.progress * 100, description=task_status.message)
            
            # 启动异步任务
            async def run_extraction():
                return await extractor.extract_from_file(input_file, task_status)
            
            # 在后台运行抽取任务
            result = asyncio.run(run_extraction())
            
            # 更新最终进度
            progress.update(task_progress, completed=100, description="处理完成")
        
        if result.success:
            # 保存知识图谱
            console.print(f"[green]✓[/green] 抽取完成，共抽取 {result.extracted_triples} 个三元组")
            
            if storage.save_knowledge_graph(result.knowledge_graph, output_file, format, compress):
                console.print(f"[green]✓[/green] 知识图谱已保存到: {output_file}")
                
                # 显示统计信息
                stats = result.knowledge_graph.get_statistics()
                console.print("\n[bold]统计信息:[/bold]")
                console.print(f"  • 总三元组数: {stats['total_triples']}")
                console.print(f"  • 唯一主语数: {stats['unique_subjects']}")
                console.print(f"  • 唯一宾语数: {stats['unique_objects']}")
                console.print(f"  • 唯一谓语数: {stats['unique_predicates']}")
                console.print(f"  • 处理时间: {result.processing_time:.2f}秒")
            else:
                console.print("[red]✗[/red] 保存知识图谱失败")
                sys.exit(1)
        else:
            console.print(f"[red]✗[/red] 抽取失败: {result.error_message}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断操作[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] 处理过程中出现错误: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option('--kg', '--knowledge-graph', 'kg_file', required=True, type=click.Path(exists=True), help='知识图谱文件路径')
@click.option('--question', '-q', help='要查询的问题')
@click.option('--interactive', '-i', is_flag=True, help='交互式问答模式')
@click.option('--max-results', type=int, default=5, help='最大显示结果数')
@click.pass_obj
def query(config: Config, kg_file: str, question: Optional[str], interactive: bool, max_results: int):
    """基于知识图谱回答问题"""
    
    # 加载知识图谱
    storage = KnowledgeStorage(config)
    reasoner = KnowledgeReasoner(config)
    
    console.print(f"[blue]加载知识图谱:[/blue] {kg_file}")
    
    try:
        knowledge_graph = storage.load_knowledge_graph(kg_file)
        if not knowledge_graph:
            console.print("[red]✗[/red] 无法加载知识图谱文件")
            sys.exit(1)
        
        console.print(f"[green]✓[/green] 知识图谱加载成功，包含 {len(knowledge_graph.triples)} 个三元组")
        
        if interactive:
            # 交互式问答模式
            console.print("\n[bold]进入交互式问答模式[/bold]")
            console.print("输入 'quit' 或 'exit' 退出\n")
            
            while True:
                try:
                    user_question = Prompt.ask("[bold cyan]请输入您的问题[/bold cyan]")
                    
                    if user_question.lower() in ['quit', 'exit', '退出']:
                        console.print("[yellow]再见！[/yellow]")
                        break
                    
                    if not user_question.strip():
                        continue
                    
                    # 查询并显示结果
                    _process_question(reasoner, knowledge_graph, user_question, console)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]退出交互模式[/yellow]")
                    break
        else:
            # 单次查询模式
            if not question:
                question = Prompt.ask("[bold cyan]请输入您的问题[/bold cyan]")
            
            _process_question(reasoner, knowledge_graph, question, console)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断操作[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] 查询过程中出现错误: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


def _process_question(reasoner: KnowledgeReasoner, knowledge_graph, question: str, console: Console):
    """处理单个问题"""
    with console.status("[bold green]正在思考...[/bold green]"):
        result = reasoner.query_sync(question, knowledge_graph)
    
    # 显示结果
    console.print(f"\n[bold]问题:[/bold] {result.question}")
    console.print(f"[bold]回答:[/bold] {result.answer}")
    console.print(f"[bold]置信度:[/bold] {result.confidence:.2f}")
    
    if result.reasoning_path:
        console.print(f"\n[bold]推理过程:[/bold]")
        for i, step in enumerate(result.reasoning_path, 1):
            console.print(f"  {i}. {step}")
    
    if result.source_triples:
        console.print(f"\n[bold]来源三元组:[/bold]")
        for i, triple in enumerate(result.source_triples, 1):
            console.print(f"  {i}. {triple}")
    
    console.print("\n" + "="*50 + "\n")


@main.command()
@click.option('--kg', '--knowledge-graph', 'kg_file', required=True, type=click.Path(exists=True), help='知识图谱文件路径')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'summary']), default='table', help='显示格式')
@click.pass_obj
def info(config: Config, kg_file: str, format: str):
    """显示知识图谱信息"""
    
    storage = KnowledgeStorage(config)
    reasoner = KnowledgeReasoner(config)
    
    try:
        knowledge_graph = storage.load_knowledge_graph(kg_file)
        if not knowledge_graph:
            console.print("[red]✗[/red] 无法加载知识图谱文件")
            sys.exit(1)
        
        stats = reasoner.get_graph_statistics(knowledge_graph)
        
        if format == 'table':
            # 表格格式显示 - 适配新的图分析结构
            table = Table(title="知识图谱统计信息")
            table.add_column("指标", style="cyan")
            table.add_column("数值", style="green")

            # 基础统计
            basic_stats = stats.get('基础统计', {})
            table.add_row("总三元组数", str(basic_stats.get('total_triples', 'N/A')))
            table.add_row("唯一实体数", str(basic_stats.get('total_entities', 'N/A')))
            table.add_row("连通实体数", str(basic_stats.get('connected_entities', 'N/A')))
            table.add_row("连通率", f"{basic_stats.get('connectivity_ratio', 0):.2%}")
            table.add_row("平均每实体三元组数", f"{basic_stats.get('avg_triples_per_entity', 0):.2f}")
            table.add_row("唯一主语数", str(basic_stats.get('unique_subjects', 'N/A')))
            table.add_row("唯一宾语数", str(basic_stats.get('unique_objects', 'N/A')))
            table.add_row("唯一谓语数", str(basic_stats.get('unique_predicates', 'N/A')))

            console.print(table)

            # 显示图结构分析
            graph_analysis = stats.get('图结构分析', {})
            if graph_analysis:
                console.print("\n[bold]图结构分析:[/bold]")
                basic_graph_stats = graph_analysis.get('基本统计', {})
                console.print(f"  • 节点数: {basic_graph_stats.get('节点数', 'N/A')}")
                console.print(f"  • 边数: {basic_graph_stats.get('边数', 'N/A')}")
                console.print(f"  • 图密度: {basic_graph_stats.get('密度', 0):.4f}")

                connectivity = graph_analysis.get('连通性', {})
                console.print(f"  • 强连通: {'是' if connectivity.get('强连通', False) else '否'}")
                console.print(f"  • 弱连通: {'是' if connectivity.get('弱连通', False) else '否'}")
                console.print(f"  • 强连通组件数: {connectivity.get('强连通组件数', 'N/A')}")
                console.print(f"  • 弱连通组件数: {connectivity.get('弱连通组件数', 'N/A')}")

            # 显示分析方法
            console.print(f"\n[bold]分析方法:[/bold] {stats.get('分析方法', 'unknown')}")
            
            # 显示最常见的谓语
            most_common_predicates = basic_stats.get('most_common_predicates', [])
            if most_common_predicates:
                console.print("\n[bold]最常见的谓语:[/bold]")
                for predicate, count in most_common_predicates:
                    console.print(f"  • {predicate}: {count}")

            # 显示最常见的实体
            most_common_subjects = basic_stats.get('most_common_subjects', [])
            if most_common_subjects:
                console.print("\n[bold]最常见的实体:[/bold]")
                for subject, count in most_common_subjects[:5]:
                    console.print(f"  • {subject}: {count}")

            # 显示中心性排名
            centralities = graph_analysis.get('中心性排名', {})
            if centralities:
                console.print("\n[bold]中心性排名:[/bold]")

                degree_central = centralities.get('度中心性前5', [])
                if degree_central:
                    console.print("  度中心性前3:")
                    for i, central in enumerate(degree_central[:3]):
                        console.print(f"    {i+1}. {central.entity}: {central.centrality_score:.4f}")

                pagerank_central = centralities.get('PageRank前5', [])
                if pagerank_central:
                    console.print("  PageRank前3:")
                    for i, central in enumerate(pagerank_central[:3]):
                        console.print(f"    {i+1}. {central.entity}: {central.centrality_score:.4f}")
        
        elif format == 'json':
            import json
            console.print(json.dumps(stats, ensure_ascii=False, indent=2))
        
        elif format == 'summary':
            # 简要摘要
            basic_stats = stats.get('基础统计', {})
            graph_analysis = stats.get('图结构分析', {})

            panel_content = f"""
总三元组数: {basic_stats.get('total_triples', 'N/A')}
唯一实体数: {basic_stats.get('total_entities', 'N/A')}
连通率: {basic_stats.get('connectivity_ratio', 0):.2%}
平均每实体三元组数: {basic_stats.get('avg_triples_per_entity', 0):.2f}

分析方法: {stats.get('分析方法', 'unknown')}
图密度: {graph_analysis.get('基本统计', {}).get('密度', 0):.4f}
强连通组件数: {graph_analysis.get('连通性', {}).get('强连通组件数', 'N/A')}
            """.strip()

            console.print(Panel(panel_content, title="知识图谱摘要", border_style="blue"))
        
    except Exception as e:
        console.print(f"[red]✗ 获取信息失败: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option('--directory', '-d', type=click.Path(), help='目录路径，默认为输出目录')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='显示格式')
@click.pass_obj
def list(config: Config, directory: Optional[str], format: str):
    """列出已保存的知识图谱文件"""
    
    storage = KnowledgeStorage(config)
    
    try:
        files = storage.list_saved_graphs(directory)
        
        if not files:
            console.print("[yellow]没有找到知识图谱文件[/yellow]")
            return
        
        if format == 'table':
            table = Table(title="知识图谱文件列表")
            table.add_column("文件名", style="cyan")
            table.add_column("格式", style="green")
            table.add_column("大小", style="yellow")
            table.add_column("三元组数", style="blue")
            table.add_column("修改时间", style="magenta")
            
            for file_info in files:
                size_str = _format_file_size(file_info['size'])
                time_str = file_info['modified_at'].strftime("%Y-%m-%d %H:%M:%S")
                triples_count = file_info.get('triples_count', 'N/A')
                
                table.add_row(
                    file_info['name'],
                    file_info['format'],
                    size_str,
                    str(triples_count),
                    time_str
                )
            
            console.print(table)
        
        elif format == 'json':
            import json
            # 转换datetime对象为字符串
            json_files = []
            for file_info in files:
                json_file = file_info.copy()
                json_file['created_at'] = file_info['created_at'].isoformat()
                json_file['modified_at'] = file_info['modified_at'].isoformat()
                json_files.append(json_file)
            
            console.print(json.dumps(json_files, ensure_ascii=False, indent=2))
        
    except Exception as e:
        console.print(f"[red]✗[/red] 列出文件失败: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--confirm', is_flag=True, help='确认删除')
@click.pass_obj
def delete(config: Config, file_path: str, confirm: bool):
    """删除知识图谱文件"""
    
    storage = KnowledgeStorage(config)
    
    try:
        if not confirm:
            if not click.confirm(f'确定要删除文件 "{file_path}" 吗？'):
                console.print("[yellow]操作已取消[/yellow]")
                return
        
        if storage.delete_graph(file_path):
            console.print(f"[green]✓[/green] 文件已删除: {file_path}")
        else:
            console.print(f"[red]✗[/red] 删除失败: {file_path}")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]✗[/red] 删除过程中出现错误: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.pass_obj
def config_show(config: Config):
    """显示当前配置"""
    
    try:
        effective_config = config.get_effective_config()
        
        import json
        console.print(Panel(
            json.dumps(effective_config, ensure_ascii=False, indent=2),
            title="当前配置",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(f"[red]✗[/red] 显示配置失败: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--from-format', type=click.Choice(['rdf', 'json', 'jsonld', 'csv', 'ttl']), help='输入格式')
@click.option('--to-format', type=click.Choice(['rdf', 'json', 'jsonld', 'csv', 'ttl']), help='输出格式')
@click.pass_obj
def convert(config: Config, input_file: str, output_file: str, from_format: Optional[str], to_format: Optional[str]):
    """转换知识图谱文件格式"""
    
    storage = KnowledgeStorage(config)
    
    try:
        console.print(f"[blue]加载知识图谱:[/blue] {input_file}")
        
        knowledge_graph = storage.load_knowledge_graph(input_file)
        if not knowledge_graph:
            console.print("[red]✗[/red] 无法加载输入文件")
            sys.exit(1)
        
        console.print(f"[green]✓[/green] 加载成功，包含 {len(knowledge_graph.triples)} 个三元组")
        
        if storage.save_knowledge_graph(knowledge_graph, output_file, to_format):
            console.print(f"[green]✓[/green] 转换完成，文件已保存到: {output_file}")
        else:
            console.print("[red]✗[/red] 保存失败")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]✗[/red] 转换过程中出现错误: {e}[/red]")
        if config.debug:
            console.print_exception()
        sys.exit(1)


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


if __name__ == '__main__':
    main()
