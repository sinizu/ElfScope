"""
ElfScope - ELF 文件分析和函数调用关系解析工具

这个包提供了 ELF 文件解析、反汇编、函数调用关系分析和调用路径查找的功能。
"""

__version__ = "1.0.0"
__author__ = "ElfScope Team"

from .core.elf_parser import ElfParser
from .core.call_analyzer import CallAnalyzer
from .core.path_finder import PathFinder
from .core.stack_analyzer import StackAnalyzer
from .utils.json_exporter import JsonExporter

__all__ = ['ElfParser', 'CallAnalyzer', 'PathFinder', 'StackAnalyzer', 'JsonExporter']
