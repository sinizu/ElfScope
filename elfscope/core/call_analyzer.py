"""
函数调用关系分析模块

该模块分析 ELF 文件中的函数调用关系，包括：
- 构建函数调用图
- 识别函数间的调用关系
- 生成调用关系数据结构
"""

from typing import Dict, List, Set, Optional, Tuple, Any
import logging
from collections import defaultdict
import networkx as nx

from .elf_parser import ElfParser
from .disassembler import Disassembler, DisassemblerError


class CallAnalyzer:
    """
    函数调用关系分析器
    
    结合 ELF 解析和反汇编功能，分析函数间的调用关系
    """
    
    def __init__(self, elf_parser: ElfParser):
        """
        初始化调用关系分析器
        
        Args:
            elf_parser: ELF 解析器实例
        """
        self.elf_parser = elf_parser
        self.architecture = elf_parser.get_architecture()
        
        try:
            self.disassembler = Disassembler(self.architecture)
        except DisassemblerError as e:
            raise ValueError(f"无法初始化反汇编器: {e}")
        
        # 调用关系数据
        self.call_graph = nx.DiGraph()  # 有向图
        self.function_calls = defaultdict(list)  # 函数 -> 调用列表
        self.call_targets = defaultdict(set)     # 地址 -> 调用该地址的函数集合
        
        # 函数地址到名称的映射
        self.addr_to_function = {}
        self.name_to_function = {}
        
        # 分析结果
        self.analyzed = False
        
        self._build_function_maps()
    
    def _build_function_maps(self) -> None:
        """构建函数地址和名称的映射"""
        functions = self.elf_parser.get_functions()
        
        for func in functions:
            addr = func['value']
            name = func['name']
            
            if addr > 0:  # 有效地址
                self.addr_to_function[addr] = func
                if name:
                    self.name_to_function[name] = func
                    # 添加节点到图中
                    self.call_graph.add_node(name, **func)
    
    def analyze(self) -> None:
        """
        执行完整的调用关系分析
        
        分析所有代码段中的函数调用关系
        """
        logging.info(f"开始分析 {self.elf_parser.filepath} 的函数调用关系")
        
        text_sections = self.elf_parser.get_text_sections()
        
        for section in text_sections:
            self._analyze_section(section)
        
        self._build_call_graph()
        self.analyzed = True
        
        logging.info(f"分析完成，发现 {len(self.call_graph.nodes)} 个函数，{len(self.call_graph.edges)} 个调用关系")
    
    def _analyze_section(self, section: Dict[str, Any]) -> None:
        """
        分析单个代码段
        
        Args:
            section: 代码段信息
        """
        section_name = section['name']
        section_data = self.elf_parser.get_section_data(section_name)
        
        if not section_data:
            logging.warning(f"无法获取段 {section_name} 的数据")
            return
        
        section_addr = section['addr']
        functions = self.elf_parser.get_functions()
        
        # 分析该段中的每个函数
        for func in functions:
            func_addr = func['value']
            func_size = func['size']
            
            # 检查函数是否在当前段中
            if (section_addr <= func_addr < section_addr + section['size'] and
                func_size > 0):
                
                self._analyze_function(func, section_data, section_addr)
    
    def _analyze_function(self, function: Dict[str, Any], 
                         section_data: bytes, 
                         section_base: int) -> None:
        """
        分析单个函数的调用关系
        
        Args:
            function: 函数信息
            section_data: 代码段数据
            section_base: 代码段基地址
        """
        func_name = function['name']
        func_addr = function['value']
        
        try:
            # 使用反汇编器分析函数调用
            calls = self.disassembler.analyze_function_calls(
                function, section_data, section_base
            )
            
            # 处理每个调用
            for call in calls:
                if 'to_address' in call:
                    target_addr = call['to_address']
                    target_func = self.elf_parser.get_function_by_address(target_addr)
                    
                    if target_func:
                        target_name = target_func['name']
                        
                        # 记录调用关系
                        call_info = {
                            'from_function': func_name,
                            'to_function': target_name,
                            'from_address': call['from_address'],
                            'to_address': target_addr,
                            'instruction': call['instruction'],
                            'type': call['type']
                        }
                        
                        self.function_calls[func_name].append(call_info)
                        self.call_targets[target_addr].add(func_name)
                    else:
                        # 可能是外部函数调用
                        call_info = {
                            'from_function': func_name,
                            'to_function': f'external_{hex(target_addr)}',
                            'from_address': call['from_address'],
                            'to_address': target_addr,
                            'instruction': call['instruction'],
                            'type': call['type'],
                            'external': True
                        }
                        
                        self.function_calls[func_name].append(call_info)
                
        except Exception as e:
            logging.warning(f"分析函数 {func_name} 时出错: {e}")
    
    def _build_call_graph(self) -> None:
        """构建调用关系图"""
        # 添加调用边
        for caller, calls in self.function_calls.items():
            for call in calls:
                callee = call['to_function']
                
                # 确保被调用函数也在图中（可能是外部函数）
                if callee not in self.call_graph:
                    self.call_graph.add_node(callee, external=call.get('external', False))
                
                # 添加调用边
                edge_data = {
                    'from_address': call['from_address'],
                    'to_address': call['to_address'],
                    'instruction': call['instruction'],
                    'type': call['type']
                }
                
                self.call_graph.add_edge(caller, callee, **edge_data)
    
    def get_call_relationships(self) -> Dict[str, Any]:
        """
        获取所有函数调用关系
        
        Returns:
            包含调用关系的字典
        """
        if not self.analyzed:
            self.analyze()
        
        relationships = {
            'functions': {},
            'calls': [],
            'statistics': {
                'total_functions': len(self.call_graph.nodes),
                'total_calls': len(self.call_graph.edges),
                'external_calls': 0
            }
        }
        
        # 函数信息
        for node in self.call_graph.nodes(data=True):
            func_name, func_data = node
            relationships['functions'][func_name] = func_data
        
        # 调用关系
        for caller, calls in self.function_calls.items():
            for call in calls:
                relationships['calls'].append(call)
                if call.get('external', False):
                    relationships['statistics']['external_calls'] += 1
        
        return relationships
    
    def get_callers(self, function_name: str) -> List[str]:
        """
        获取调用指定函数的所有函数
        
        Args:
            function_name: 目标函数名
            
        Returns:
            调用者函数名列表
        """
        if not self.analyzed:
            self.analyze()
        
        return list(self.call_graph.predecessors(function_name))
    
    def get_callees(self, function_name: str) -> List[str]:
        """
        获取指定函数调用的所有函数
        
        Args:
            function_name: 源函数名
            
        Returns:
            被调用函数名列表
        """
        if not self.analyzed:
            self.analyze()
        
        return list(self.call_graph.successors(function_name))
    
    def get_call_details(self, from_function: str, to_function: str) -> List[Dict[str, Any]]:
        """
        获取两个函数间的详细调用信息
        
        Args:
            from_function: 调用方函数名
            to_function: 被调用方函数名
            
        Returns:
            调用详情列表
        """
        if not self.analyzed:
            self.analyze()
        
        details = []
        
        for call in self.function_calls.get(from_function, []):
            if call['to_function'] == to_function:
                details.append(call)
        
        return details
    
    def is_recursive_function(self, function_name: str) -> bool:
        """
        检查函数是否递归调用自己
        
        Args:
            function_name: 函数名
            
        Returns:
            是否为递归函数
        """
        if not self.analyzed:
            self.analyze()
        
        return self.call_graph.has_edge(function_name, function_name)
    
    def find_cycles(self) -> List[List[str]]:
        """
        查找调用图中的环（相互递归调用）
        
        Returns:
            环的列表，每个环是函数名列表
        """
        if not self.analyzed:
            self.analyze()
        
        try:
            cycles = list(nx.simple_cycles(self.call_graph))
            return cycles
        except Exception as e:
            logging.warning(f"查找环时出错: {e}")
            return []
    
    def get_function_depth(self, function_name: str) -> int:
        """
        计算函数的调用深度（最长调用链长度）
        
        Args:
            function_name: 函数名
            
        Returns:
            调用深度
        """
        if not self.analyzed:
            self.analyze()
        
        if function_name not in self.call_graph:
            return 0
        
        try:
            # 计算从该函数出发的最长路径
            lengths = nx.single_source_shortest_path_length(
                self.call_graph, function_name
            )
            return max(lengths.values()) if lengths else 0
        except Exception as e:
            logging.warning(f"计算函数深度时出错: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取调用关系统计信息
        
        Returns:
            统计信息字典
        """
        if not self.analyzed:
            self.analyze()
        
        stats = {
            'total_functions': len(self.call_graph.nodes),
            'total_calls': len(self.call_graph.edges),
            'average_calls_per_function': 0,
            'max_calls_from_function': 0,
            'max_calls_to_function': 0,
            'recursive_functions': 0,
            'external_functions': 0,
            'cycles': len(self.find_cycles())
        }
        
        if stats['total_functions'] > 0:
            stats['average_calls_per_function'] = stats['total_calls'] / stats['total_functions']
        
        # 计算每个函数的调用统计
        for node in self.call_graph.nodes:
            out_degree = self.call_graph.out_degree(node)
            in_degree = self.call_graph.in_degree(node)
            
            stats['max_calls_from_function'] = max(stats['max_calls_from_function'], out_degree)
            stats['max_calls_to_function'] = max(stats['max_calls_to_function'], in_degree)
            
            if self.is_recursive_function(node):
                stats['recursive_functions'] += 1
            
            node_data = self.call_graph.nodes[node]
            if node_data.get('external', False):
                stats['external_functions'] += 1
        
        return stats
