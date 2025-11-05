#!/usr/bin/env python3
"""
ElfScope MCP 服务器

基于 FastMCP 框架实现的 Model Context Protocol 服务器，
将 ElfScope 的所有 CLI 功能暴露为 MCP 工具，供其他应用程序调用。

使用方法:
    python -m elfscope.mcp_server
    或
    elfscope-mcp

支持的工具:
    - elfscope_info: 获取ELF文件基本信息
    - elfscope_analyze: 分析函数调用关系
    - elfscope_paths: 查找调用路径
    - elfscope_complete: 完整分析
    - elfscope_function: 分析特定函数
    - elfscope_summary: 生成摘要报告
    - elfscope_stack: 栈使用分析
    - elfscope_stack_summary: 栈使用摘要
    - elfscope_objdump: objdump功能
"""

import os
import sys
import logging
import time
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCP = None

from .core.elf_parser import ElfParser
from .core.call_analyzer import CallAnalyzer
from .core.path_finder import PathFinder
from .core.stack_analyzer import StackAnalyzer
from .core.objdump import ObjdumpAnalyzer
from .utils.json_exporter import JsonExporter


# 配置日志输出到 stderr（不影响 stdio MCP 通信）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger("elfscope-mcp")


# ============================================================================
# 辅助函数
# ============================================================================

def _wrap_result(data: Any, tool_name: str, execution_time: float) -> Dict[str, Any]:
    """
    包装成功结果为统一格式
    
    Args:
        data: 实际结果数据
        tool_name: 工具名称
        execution_time: 执行时间（秒）
        
    Returns:
        统一格式的结果字典
    """
    return {
        "success": True,
        "data": data,
        "metadata": {
            "tool": tool_name,
            "version": "1.0.0",
            "execution_time": round(execution_time, 3),
            "timestamp": datetime.now().isoformat()
        }
    }


def _wrap_error(error: Exception, tool_name: str) -> Dict[str, Any]:
    """
    包装错误结果为统一格式
    
    Args:
        error: 异常对象
        tool_name: 工具名称
        
    Returns:
        统一格式的错误字典
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    logger.error(f"Tool {tool_name} error: {error_type}: {error_message}")
    logger.debug(traceback.format_exc())
    
    return {
        "success": False,
        "error": error_message,
        "error_type": error_type,
        "metadata": {
            "tool": tool_name,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    }


def _validate_file(elf_file: str) -> None:
    """
    验证文件路径是否有效
    
    Args:
        elf_file: ELF 文件路径
        
    Raises:
        FileNotFoundError: 文件不存在
        PermissionError: 文件不可读
        ValueError: 路径不是文件
    """
    if not os.path.exists(elf_file):
        raise FileNotFoundError(f"文件不存在: {elf_file}")
    
    if not os.path.isfile(elf_file):
        raise ValueError(f"路径不是文件: {elf_file}")
    
    if not os.access(elf_file, os.R_OK):
        raise PermissionError(f"文件不可读: {elf_file}")


# ============================================================================
# 工具实现函数（可被测试直接调用）
# ============================================================================

def elfscope_info(elf_file: str) -> dict:
    """获取 ELF 文件的基本信息"""
    start_time = time.time()
    tool_name = "elfscope_info"
    
    try:
        _validate_file(elf_file)
        
        elf_parser = ElfParser(elf_file)
        file_info = elf_parser.get_file_info()
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(file_info, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_analyze(
    elf_file: str,
    include_stats: bool = True,
    include_details: bool = True
) -> dict:
    """分析 ELF 文件的函数调用关系"""
    start_time = time.time()
    tool_name = "elfscope_analyze"
    
    try:
        _validate_file(elf_file)
        
        # 初始化解析器和分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        
        # 执行分析
        call_analyzer.analyze()
        
        # 构建结果数据
        result_data = {
            "metadata": {
                "tool_name": "ElfScope",
                "version": "1.0.0",
                "export_time": datetime.now().isoformat(),
                "elf_file": elf_file,
                "architecture": elf_parser.get_architecture()
            }
        }
        
        # 获取调用关系和函数信息
        relationships = call_analyzer.get_call_relationships()
        
        if include_details:
            result_data["functions"] = relationships.get("functions", {})
        
        result_data["call_relationships"] = relationships.get("calls", [])
        
        if include_stats:
            stats = call_analyzer.get_statistics()
            result_data["statistics"] = stats
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(result_data, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_paths(
    elf_file: str,
    target_function: str,
    source_function: Optional[str] = None,
    max_depth: int = 10,
    include_cycles: bool = False
) -> dict:
    """查找函数间的调用路径"""
    start_time = time.time()
    tool_name = "elfscope_paths"
    
    try:
        _validate_file(elf_file)
        
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        call_analyzer.analyze()
        
        # 查找路径
        path_finder = PathFinder(call_analyzer)
        paths = path_finder.find_paths(
            target_function=target_function,
            source_function=source_function,
            max_depth=max_depth,
            include_cycles=include_cycles
        )
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(paths, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_complete(elf_file: str) -> dict:
    """执行完整的 ELF 文件分析"""
    start_time = time.time()
    tool_name = "elfscope_complete"
    
    try:
        _validate_file(elf_file)
        
        # 初始化所有组件
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        call_analyzer.analyze()
        
        # 获取调用关系
        relationships = call_analyzer.get_call_relationships()
        
        # 构建完整结果
        result_data = {
            "file_info": elf_parser.get_file_info(),
            "functions": relationships.get("functions", {}),
            "call_relationships": relationships.get("calls", []),
            "statistics": call_analyzer.get_statistics(),
            "metadata": {
                "tool_name": "ElfScope",
                "version": "1.0.0",
                "analysis_time": datetime.now().isoformat(),
                "elf_file": elf_file,
                "architecture": elf_parser.get_architecture()
            }
        }
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(result_data, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_function(elf_file: str, function_name: str) -> dict:
    """分析特定函数的详细信息"""
    start_time = time.time()
    tool_name = "elfscope_function"
    
    try:
        _validate_file(elf_file)
        
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        call_analyzer.analyze()
        
        # 检查函数是否存在
        if function_name not in call_analyzer.call_graph:
            # 查找相似函数名
            all_functions = list(call_analyzer.call_graph.nodes)
            similar_functions = [f for f in all_functions if function_name.lower() in f.lower()]
            
            error_msg = f"函数 '{function_name}' 不存在"
            if similar_functions:
                error_msg += f"。可能的函数名: {', '.join(similar_functions[:5])}"
            
            raise ValueError(error_msg)
        
        # 获取函数信息
        callers = call_analyzer.get_callers(function_name)
        callees = call_analyzer.get_callees(function_name)
        is_recursive = call_analyzer.is_recursive_function(function_name)
        
        # 获取函数详细信息
        function_info = call_analyzer.call_graph.nodes.get(function_name, {})
        
        result_data = {
            "function_name": function_name,
            "function_info": function_info,
            "callers": callers,
            "callees": callees,
            "is_recursive": is_recursive,
            "caller_count": len(callers),
            "callee_count": len(callees),
            "metadata": {
                "architecture": elf_parser.get_architecture()
            }
        }
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(result_data, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_summary(elf_file: str) -> dict:
    """生成 ELF 文件的分析摘要报告"""
    start_time = time.time()
    tool_name = "elfscope_summary"
    
    try:
        _validate_file(elf_file)
        
        # 快速分析
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        call_analyzer.analyze()
        
        # 生成摘要
        stats = call_analyzer.get_statistics()
        file_info = elf_parser.get_file_info()
        
        # 复杂度评估
        complexity = "simple"
        if stats["total_functions"] > 100 or stats["total_calls"] > 500:
            complexity = "high"
        elif stats["total_functions"] > 50 or stats["total_calls"] > 200:
            complexity = "moderate"
        
        result_data = {
            "file_info": file_info,
            "statistics": stats,
            "complexity_assessment": complexity,
            "has_recursion": stats["recursive_functions"] > 0,
            "has_cycles": stats["cycles"] > 0,
            "metadata": {
                "analysis_time": datetime.now().isoformat()
            }
        }
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(result_data, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_stack(elf_file: str, function_name: str) -> dict:
    """分析指定函数的栈使用情况"""
    start_time = time.time()
    tool_name = "elfscope_stack"
    
    try:
        _validate_file(elf_file)
        
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        stack_analyzer = StackAnalyzer(call_analyzer)
        
        # 分析栈使用
        stack_info = stack_analyzer.get_function_stack_info(function_name)
        
        if not stack_info.get('found', False):
            raise ValueError(stack_info.get('error', f"无法分析函数 '{function_name}' 的栈信息"))
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(stack_info, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_stack_summary(elf_file: str, top: int = 10) -> dict:
    """生成程序的栈使用情况摘要"""
    start_time = time.time()
    tool_name = "elfscope_stack_summary"
    
    try:
        _validate_file(elf_file)
        
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        call_analyzer = CallAnalyzer(elf_parser)
        stack_analyzer = StackAnalyzer(call_analyzer)
        
        # 生成摘要
        summary = stack_analyzer.get_stack_summary()
        heavy_functions = stack_analyzer.find_stack_heavy_functions(limit=top)
        
        result_data = {
            "summary": summary,
            "heavy_functions": heavy_functions
        }
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(result_data, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


def elfscope_objdump(
    elf_file: str,
    disassemble: bool = False,
    function: Optional[str] = None,
    syms: bool = False,
    headers: bool = False,
    start_addr: Optional[str] = None,
    stop_addr: Optional[str] = None
) -> dict:
    """显示 ELF 文件信息（类似 GNU objdump）"""
    start_time = time.time()
    tool_name = "elfscope_objdump"
    
    try:
        _validate_file(elf_file)
        
        # 初始化分析器
        elf_parser = ElfParser(elf_file)
        objdump_analyzer = ObjdumpAnalyzer(elf_parser)
        
        result_data = {}
        
        # 处理反汇编
        if disassemble or function or start_addr:
            if function:
                disasm_result = objdump_analyzer.disassemble_function(function)
                result_data['disassembly'] = disasm_result
            elif start_addr:
                start = int(start_addr, 16) if isinstance(start_addr, str) else start_addr
                stop = int(stop_addr, 16) if stop_addr and isinstance(stop_addr, str) else None
                disasm_result = objdump_analyzer.disassemble_section(
                    start_address=start,
                    end_address=stop
                )
                result_data['disassembly'] = disasm_result
            else:
                disasm_result = objdump_analyzer.disassemble_section()
                result_data['disassembly'] = disasm_result
        
        # 处理符号表
        if syms:
            symbols_result = objdump_analyzer.show_symbols()
            result_data['symbols'] = symbols_result
        
        # 处理节区头
        if headers:
            headers_result = objdump_analyzer.show_headers()
            result_data['headers'] = headers_result
        
        elf_parser.close()
        
        execution_time = time.time() - start_time
        return _wrap_result(result_data, tool_name, execution_time)
        
    except Exception as e:
        return _wrap_error(e, tool_name)


# ============================================================================
# FastMCP 工具注册（仅当 FastMCP 可用时）
# ============================================================================

if FASTMCP_AVAILABLE:
    # 创建 MCP 服务器实例
    mcp = FastMCP(
        "ElfScope",
        dependencies=["pyelftools>=0.29", "capstone>=4.0.2", "networkx>=2.8"]
    )
    
    # 注册所有工具
    @mcp.tool(name="elfscope_info")
    def tool_elfscope_info(elf_file: str) -> dict:
        """获取 ELF 文件的基本信息
        
        分析并返回 ELF 文件的架构、文件类型、入口点、段数量、符号数量等基本信息。
        
        Args:
            elf_file: ELF 文件的路径
        """
        return elfscope_info(elf_file)
    
    @mcp.tool(name="elfscope_analyze")
    def tool_elfscope_analyze(
        elf_file: str,
        include_stats: bool = True,
        include_details: bool = True
    ) -> dict:
        """分析 ELF 文件的函数调用关系
        
        深度分析二进制文件中的所有函数及其调用关系，构建完整的调用图。
        
        Args:
            elf_file: ELF 文件的路径
            include_stats: 是否包含统计信息（默认 True）
            include_details: 是否包含函数详细信息（默认 True）
        """
        return elfscope_analyze(elf_file, include_stats, include_details)
    
    @mcp.tool(name="elfscope_paths")
    def tool_elfscope_paths(
        elf_file: str,
        target_function: str,
        source_function: Optional[str] = None,
        max_depth: int = 10,
        include_cycles: bool = False
    ) -> dict:
        """查找函数间的调用路径
        
        在函数调用图中搜索从源函数到目标函数的所有调用路径。
        
        Args:
            elf_file: ELF 文件的路径
            target_function: 目标函数名称
            source_function: 源函数名称（可选）
            max_depth: 最大搜索深度（默认 10）
            include_cycles: 是否包含存在环的路径（默认 False）
        """
        return elfscope_paths(elf_file, target_function, source_function, max_depth, include_cycles)
    
    @mcp.tool(name="elfscope_complete")
    def tool_elfscope_complete(elf_file: str) -> dict:
        """执行完整的 ELF 文件分析
        
        对 ELF 文件进行全面分析，包括文件信息、函数列表、调用关系、统计信息等。
        
        Args:
            elf_file: ELF 文件的路径
        """
        return elfscope_complete(elf_file)
    
    @mcp.tool(name="elfscope_function")
    def tool_elfscope_function(elf_file: str, function_name: str) -> dict:
        """分析特定函数的详细信息
        
        获取指定函数的调用者、被调用函数、递归信息等详细信息。
        
        Args:
            elf_file: ELF 文件的路径
            function_name: 要分析的函数名称
        """
        return elfscope_function(elf_file, function_name)
    
    @mcp.tool(name="elfscope_summary")
    def tool_elfscope_summary(elf_file: str) -> dict:
        """生成 ELF 文件的分析摘要报告
        
        快速生成包含关键统计信息和复杂度评估的摘要报告。
        
        Args:
            elf_file: ELF 文件的路径
        """
        return elfscope_summary(elf_file)
    
    @mcp.tool(name="elfscope_stack")
    def tool_elfscope_stack(elf_file: str, function_name: str) -> dict:
        """分析指定函数的栈使用情况
        
        分析函数的本地栈帧大小以及通过调用链的最大栈消耗。
        
        Args:
            elf_file: ELF 文件的路径
            function_name: 要分析的函数名称
        """
        return elfscope_stack(elf_file, function_name)
    
    @mcp.tool(name="elfscope_stack_summary")
    def tool_elfscope_stack_summary(elf_file: str, top: int = 10) -> dict:
        """生成程序的栈使用情况摘要
        
        分析整个程序的栈使用模式，找出栈消耗最大的函数。
        
        Args:
            elf_file: ELF 文件的路径
            top: 显示栈消耗最大的函数数量（默认 10）
        """
        return elfscope_stack_summary(elf_file, top)
    
    @mcp.tool(name="elfscope_objdump")
    def tool_elfscope_objdump(
        elf_file: str,
        disassemble: bool = False,
        function: Optional[str] = None,
        syms: bool = False,
        headers: bool = False,
        start_addr: Optional[str] = None,
        stop_addr: Optional[str] = None
    ) -> dict:
        """显示 ELF 文件信息（类似 GNU objdump）
        
        提供反汇编、符号表、节区头等信息的查看功能。
        
        Args:
            elf_file: ELF 文件的路径
            disassemble: 是否反汇编代码段（默认 False）
            function: 要反汇编的函数名称（可选）
            syms: 是否显示符号表（默认 False）
            headers: 是否显示节区头（默认 False）
            start_addr: 起始地址（十六进制字符串）
            stop_addr: 结束地址（十六进制字符串）
        """
        return elfscope_objdump(elf_file, disassemble, function, syms, headers, start_addr, stop_addr)


# ============================================================================
# 主函数
# ============================================================================

def main():
    """MCP 服务器主入口"""
    if not FASTMCP_AVAILABLE:
        logger.error("FastMCP 未安装！请运行: pip install fastmcp")
        print("错误: FastMCP 未安装！", file=sys.stderr)
        print("请运行: pip install fastmcp", file=sys.stderr)
        sys.exit(1)
    
    logger.info("Starting ElfScope MCP Server...")
    logger.info("Server will communicate via stdio (standard input/output)")
    logger.info("Available tools: elfscope_info, elfscope_analyze, elfscope_paths, "
                "elfscope_complete, elfscope_function, elfscope_summary, "
                "elfscope_stack, elfscope_stack_summary, elfscope_objdump")
    
    try:
        # 运行 MCP 服务器（使用 stdio 传输）
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
