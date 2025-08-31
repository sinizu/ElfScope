"""
命令行接口模块

提供 ElfScope 工具的命令行接口，支持：
- 分析 ELF 文件的函数调用关系
- 查找函数间的调用路径
- 导出分析结果为 JSON 格式
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

import click

from .core.elf_parser import ElfParser
from .core.call_analyzer import CallAnalyzer
from .core.path_finder import PathFinder
from .core.stack_analyzer import StackAnalyzer
from .utils.json_exporter import JsonExporter


def setup_logging(verbose: bool = False):
    """设置日志配置"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )


@click.group()
@click.version_option(version='1.0.0', prog_name='ElfScope')
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
def cli(verbose):
    """
    ElfScope - ELF 文件函数调用关系分析工具
    
    分析 ELF 文件中的函数调用关系，支持多种架构的反汇编和调用路径查找。
    """
    setup_logging(verbose)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.option('--output', '-o', required=True, help='输出 JSON 文件路径')
@click.option('--include-stats', is_flag=True, default=True, help='包含统计信息')
@click.option('--include-details', is_flag=True, default=True, help='包含函数详细信息')
def analyze(elf_file: str, output: str, include_stats: bool, include_details: bool):
    """
    分析 ELF 文件的函数调用关系
    
    \b
    示例:
        elfscope analyze /path/to/binary -o analysis.json
        elfscope analyze ./program -o results.json --include-stats --include-details
    """
    try:
        click.echo(f"正在分析 ELF 文件: {elf_file}")
        
        # 初始化解析器
        elf_parser = ElfParser(elf_file)
        click.echo(f"架构: {elf_parser.get_architecture()}")
        click.echo(f"函数数量: {len(elf_parser.get_functions())}")
        
        # 分析调用关系
        call_analyzer = CallAnalyzer(elf_parser)
        with click.progressbar(length=100, label='分析调用关系') as bar:
            call_analyzer.analyze()
            bar.update(100)
        
        # 获取统计信息
        stats = call_analyzer.get_statistics()
        click.echo(f"发现调用关系: {stats['total_calls']}")
        click.echo(f"外部函数: {stats['external_functions']}")
        
        # 导出结果
        exporter = JsonExporter()
        success = exporter.export_call_relationships(
            call_analyzer=call_analyzer,
            output_file=output,
            include_statistics=include_stats,
            include_function_details=include_details
        )
        
        if success:
            click.echo(f"✓ 分析结果已保存到: {output}")
        else:
            click.echo("✗ 导出失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 分析失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.argument('target_function')
@click.option('--source', '-s', help='源函数名（可选）')
@click.option('--output', '-o', required=True, help='输出 JSON 文件路径')
@click.option('--max-depth', '-d', default=10, help='最大搜索深度')
@click.option('--include-cycles', is_flag=True, help='包含存在环的路径')
def paths(elf_file: str, target_function: str, source: Optional[str], 
         output: str, max_depth: int, include_cycles: bool):
    """
    查找函数调用路径
    
    \b
    示例:
        # 查找所有到 target_func 的调用路径
        elfscope paths /path/to/binary target_func -o paths.json
        
        # 查找从 source_func 到 target_func 的路径
        elfscope paths /path/to/binary target_func -s source_func -o paths.json
        
        # 限制搜索深度并包含环
        elfscope paths /path/to/binary target_func -d 5 --include-cycles -o paths.json
    """
    try:
        click.echo(f"正在分析 ELF 文件: {elf_file}")
        
        # 初始化解析器和分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        
        with click.progressbar(length=100, label='分析调用关系') as bar:
            call_analyzer.analyze()
            bar.update(100)
        
        # 查找路径
        path_finder = PathFinder(call_analyzer)
        click.echo(f"查找到函数 '{target_function}' 的调用路径...")
        
        if source:
            click.echo(f"从函数 '{source}' 开始搜索")
        else:
            click.echo("搜索所有可能的调用路径")
        
        # 导出路径
        exporter = JsonExporter()
        success = exporter.export_call_paths(
            path_finder=path_finder,
            target_function=target_function,
            source_function=source,
            output_file=output,
            max_depth=max_depth,
            include_cycles=include_cycles
        )
        
        if success:
            click.echo(f"✓ 调用路径已保存到: {output}")
        else:
            click.echo("✗ 导出失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 路径查找失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.option('--output', '-o', required=True, help='输出 JSON 文件路径')
def complete(elf_file: str, output: str):
    """
    进行完整的 ELF 文件分析
    
    \b
    示例:
        elfscope complete /path/to/binary -o complete_analysis.json
    """
    try:
        click.echo(f"正在进行完整分析: {elf_file}")
        
        # 初始化所有组件
        elf_parser = ElfParser(elf_file)
        click.echo(f"ELF 信息: {elf_parser.get_architecture()}, "
                  f"入口点: {hex(elf_parser.get_entry_point())}")
        
        call_analyzer = CallAnalyzer(elf_parser)
        
        with click.progressbar(length=100, label='执行完整分析') as bar:
            call_analyzer.analyze()
            bar.update(100)
        
        # 显示分析摘要
        stats = call_analyzer.get_statistics()
        click.echo("\n分析摘要:")
        click.echo(f"  函数总数: {stats['total_functions']}")
        click.echo(f"  调用关系: {stats['total_calls']}")
        click.echo(f"  递归函数: {stats['recursive_functions']}")
        click.echo(f"  外部函数: {stats['external_functions']}")
        click.echo(f"  调用环: {stats['cycles']}")
        
        # 导出完整分析结果
        exporter = JsonExporter()
        success = exporter.export_complete_analysis(
            elf_parser=elf_parser,
            call_analyzer=call_analyzer,
            output_file=output
        )
        
        if success:
            click.echo(f"✓ 完整分析结果已保存到: {output}")
        else:
            click.echo("✗ 导出失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 完整分析失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.argument('function_name')
@click.option('--output', '-o', required=True, help='输出 JSON 文件路径')
def function(elf_file: str, function_name: str, output: str):
    """
    分析特定函数的详细信息
    
    \b
    示例:
        elfscope function /path/to/binary main -o main_details.json
        elfscope function ./program my_function -o function_info.json
    """
    try:
        click.echo(f"正在分析函数 '{function_name}' 在文件: {elf_file}")
        
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        call_analyzer.analyze()
        
        # 检查函数是否存在
        if function_name not in call_analyzer.call_graph:
            click.echo(f"✗ 函数 '{function_name}' 不存在", err=True)
            # 建议相似的函数名
            all_functions = list(call_analyzer.call_graph.nodes)
            similar_functions = [f for f in all_functions if function_name.lower() in f.lower()]
            if similar_functions:
                click.echo("可能的函数名:")
                for func in similar_functions[:5]:
                    click.echo(f"  - {func}")
            sys.exit(1)
        
        # 获取函数信息
        callers = call_analyzer.get_callers(function_name)
        callees = call_analyzer.get_callees(function_name)
        is_recursive = call_analyzer.is_recursive_function(function_name)
        
        click.echo(f"\n函数信息:")
        click.echo(f"  调用者数量: {len(callers)}")
        click.echo(f"  被调用函数数量: {len(callees)}")
        click.echo(f"  是否递归: {'是' if is_recursive else '否'}")
        
        # 导出详细信息
        exporter = JsonExporter()
        success = exporter.export_function_details(
            call_analyzer=call_analyzer,
            function_name=function_name,
            output_file=output
        )
        
        if success:
            click.echo(f"✓ 函数详情已保存到: {output}")
        else:
            click.echo("✗ 导出失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 函数分析失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.option('--output', '-o', required=True, help='输出摘要报告路径')
def summary(elf_file: str, output: str):
    """
    生成分析摘要报告
    
    \b
    示例:
        elfscope summary /path/to/binary -o summary.json
    """
    try:
        click.echo(f"正在生成摘要报告: {elf_file}")
        
        # 快速分析
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        call_analyzer.analyze()
        
        # 生成摘要报告
        exporter = JsonExporter()
        success = exporter.create_summary_report(
            elf_parser=elf_parser,
            call_analyzer=call_analyzer,
            output_file=output
        )
        
        if success:
            click.echo(f"✓ 摘要报告已保存到: {output}")
            
            # 显示简要统计
            stats = call_analyzer.get_statistics()
            click.echo("\n快速统计:")
            click.echo(f"  函数数量: {stats['total_functions']}")
            click.echo(f"  调用关系: {stats['total_calls']}")
            click.echo(f"  复杂度评估: {exporter._assess_complexity(stats)}")
        else:
            click.echo("✗ 生成摘要报告失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 生成摘要报告失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.argument('function_name')
@click.option('--output', '-o', help='输出 JSON 文件路径（可选）')
def stack(elf_file: str, function_name: str, output: Optional[str]):
    """
    分析指定函数的栈使用情况
    
    分析函数的本地栈帧大小以及通过调用链的最大栈消耗。
    
    \b
    示例:
        elfscope stack /path/to/binary main
        elfscope stack /path/to/binary fibonacci_recursive -o stack_info.json
    """
    try:
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        stack_analyzer = StackAnalyzer(call_analyzer)
        
        click.echo(f"正在分析函数 '{function_name}' 的栈使用情况...")
        
        # 分析栈使用
        stack_info = stack_analyzer.get_function_stack_info(function_name)
        
        if not stack_info['found']:
            click.echo(f"✗ {stack_info['error']}", err=True)
            sys.exit(1)
        
        # 显示结果
        click.echo(f"\n函数栈分析: {function_name}")
        click.echo("=" * 50)
        click.echo(f"架构:           {stack_info['architecture']}")
        click.echo(f"本地栈帧:       {stack_info['local_stack_frame']} 字节")
        click.echo(f"最大总栈消耗:   {stack_info['max_total_stack']} 字节")
        click.echo(f"调用栈消耗:     {stack_info['stack_consumed_by_calls']} 字节")
        
        # 显示最大栈消耗的调用路径
        if stack_info.get('max_stack_call_path'):
            click.echo(f"\n最大栈消耗调用路径:")
            path = stack_info['max_stack_call_path']
            for i, func in enumerate(path):
                indent = "  " * i
                click.echo(f"{indent}└─ {func}")
        
        # 显示路径详情（如果有的话）
        if stack_info.get('max_stack_path_details'):
            click.echo(f"\n路径栈消耗详情:")
            for detail in stack_info['max_stack_path_details']:
                recursive_mark = " (递归)" if detail.get('is_recursive') else ""
                external_mark = " (外部)" if detail.get('is_external') else ""
                click.echo(f"  {detail['function']}: {detail['local_stack']}B → "
                          f"累计: {detail['cumulative_stack']}B{recursive_mark}{external_mark}")
        
        if stack_info['called_functions']:
            click.echo(f"\n直接调用的函数 ({len(stack_info['called_functions'])}):")
            for callee in stack_info['called_functions']:
                external_mark = " (外部)" if callee['external'] else ""
                click.echo(f"  {callee['function']}: {callee['stack_frame']} 字节{external_mark}")
        
        # 输出到文件（如果指定）
        if output:
            exporter = JsonExporter()
            success = exporter.export_data(stack_info, output)
            if success:
                click.echo(f"\n✓ 栈分析结果已保存到: {output}")
            else:
                click.echo(f"\n✗ 保存结果失败", err=True)
                
    except Exception as e:
        click.echo(f"✗ 栈分析失败: {e}", err=True)
        sys.exit(1)


@cli.command(name='stack-summary')
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
@click.option('--output', '-o', help='输出 JSON 文件路径（可选）')
@click.option('--top', '-t', default=10, help='显示栈消耗最大的函数数量')
def stack_summary(elf_file: str, output: Optional[str], top: int):
    """
    生成程序的栈使用情况摘要
    
    分析整个程序的栈使用模式，找出栈消耗最大的函数。
    
    \b
    示例:
        elfscope stack-summary /path/to/binary
        elfscope stack-summary /path/to/binary -o stack_summary.json -t 20
    """
    try:
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        stack_analyzer = StackAnalyzer(call_analyzer)
        
        click.echo("正在分析程序的栈使用情况...")
        
        # 生成摘要
        summary = stack_analyzer.get_stack_summary()
        heavy_functions = stack_analyzer.find_stack_heavy_functions(limit=top)
        
        # 显示摘要
        click.echo(f"\n栈使用摘要: {elf_file}")
        click.echo("=" * 50)
        click.echo(f"架构:               {summary['architecture']}")
        click.echo(f"分析函数总数:       {summary['total_functions_analyzed']}")
        click.echo(f"有栈消耗函数:       {summary['functions_with_stack']}")
        click.echo(f"最大本地栈帧:       {summary['max_local_stack_frame']} 字节")
        click.echo(f"最大总栈消耗:       {summary['max_total_stack_consumption']} 字节")
        
        if summary['function_with_max_local_stack']:
            click.echo(f"最大本地栈函数:     {summary['function_with_max_local_stack']}")
        if summary['function_with_max_total_stack']:
            click.echo(f"最大总栈函数:       {summary['function_with_max_total_stack']}")
        
        # 显示最大栈消耗的调用路径
        if summary.get('max_total_stack_call_path'):
            click.echo(f"\n最大栈消耗调用路径:")
            path = summary['max_total_stack_call_path']
            for i, func in enumerate(path):
                indent = "  " * i
                click.echo(f"{indent}└─ {func}")
        
        click.echo(f"\n栈指针寄存器:       {summary['stack_pointer_register']}")
        click.echo(f"栈对齐要求:         {summary['stack_alignment']} 字节")
        
        # 栈使用分布
        dist = summary['stack_distribution']
        click.echo(f"\n栈使用分布:")
        click.echo(f"  小栈消耗 (<64B):     {dist['small']} 函数")
        click.echo(f"  中等栈消耗 (64-256B): {dist['medium']} 函数") 
        click.echo(f"  大栈消耗 (256-1KB):   {dist['large']} 函数")
        click.echo(f"  巨大栈消耗 (>1KB):    {dist['huge']} 函数")
        
        # 栈消耗最大的函数
        if heavy_functions:
            click.echo(f"\n栈消耗最大的 {min(top, len(heavy_functions))} 个函数:")
            for i, func in enumerate(heavy_functions):
                ratio_text = f" (比例: {func['stack_ratio']:.1f}x)" if func['stack_ratio'] > 0 else ""
                click.echo(f"  {i+1:2d}. {func['function']: <25} "
                          f"总计: {func['max_total_stack']:4d}B "
                          f"本地: {func['local_stack_frame']:4d}B{ratio_text}")
                
                # 显示调用路径（简化版本，只显示前5个函数）
                if func.get('max_stack_call_path') and len(func['max_stack_call_path']) > 1:
                    path = func['max_stack_call_path'][:5]  # 限制显示长度
                    path_str = " → ".join(path)
                    if len(func['max_stack_call_path']) > 5:
                        path_str += " → ..."
                    click.echo(f"      路径: {path_str}")
        
        # 输出到文件（如果指定）
        if output:
            full_data = {
                'summary': summary,
                'heavy_functions': heavy_functions
            }
            exporter = JsonExporter()
            success = exporter.export_data(full_data, output)
            if success:
                click.echo(f"\n✓ 栈摘要已保存到: {output}")
            else:
                click.echo(f"\n✗ 保存结果失败", err=True)
                
    except Exception as e:
        click.echo(f"✗ 栈分析失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('elf_file', type=click.Path(exists=True, readable=True))
def info(elf_file: str):
    """
    显示 ELF 文件基本信息
    
    \b
    示例:
        elfscope info /path/to/binary
    """
    try:
        elf_parser = ElfParser(elf_file)
        file_info = elf_parser.get_file_info()
        
        click.echo(f"\nELF 文件信息: {elf_file}")
        click.echo("=" * 50)
        click.echo(f"架构:       {file_info['architecture']}")
        click.echo(f"文件类型:   {file_info['file_type']}")
        click.echo(f"入口点:     {file_info['entry_point']}")
        click.echo(f"段数量:     {file_info['num_sections']}")
        click.echo(f"符号数量:   {file_info['num_symbols']}")
        click.echo(f"函数数量:   {file_info['num_functions']}")
        click.echo(f"代码段数量: {file_info['text_sections']}")
        
        # 显示主要函数（如果存在）
        functions = elf_parser.get_functions()
        if functions:
            click.echo(f"\n主要函数:")
            main_functions = [f for f in functions if f['name'] in ['main', '_start', '__libc_start_main']]
            if main_functions:
                for func in main_functions:
                    click.echo(f"  {func['name']} @ {hex(func['value'])}")
            else:
                # 显示前几个函数
                for func in functions[:5]:
                    if func['name']:
                        click.echo(f"  {func['name']} @ {hex(func['value'])}")
                if len(functions) > 5:
                    click.echo(f"  ... 还有 {len(functions) - 5} 个函数")
        
    except Exception as e:
        click.echo(f"✗ 获取 ELF 信息失败: {e}", err=True)
        sys.exit(1)


def main():
    """主入口点"""
    cli()


if __name__ == '__main__':
    main()
