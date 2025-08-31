"""
JSON 导出模块

该模块提供将分析结果导出为 JSON 格式的功能，包括：
- 函数调用关系导出
- 调用路径导出
- 统计信息导出
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from ..core.elf_parser import ElfParser
from ..core.call_analyzer import CallAnalyzer
from ..core.path_finder import PathFinder


class JsonExporter:
    """
    JSON 导出器
    
    负责将 ELF 分析结果格式化并导出为 JSON 文件
    """
    
    def __init__(self):
        """初始化导出器"""
        self.default_indent = 2
        self.ensure_ascii = False
    
    def export_call_relationships(self, 
                                call_analyzer: CallAnalyzer, 
                                output_file: str,
                                include_statistics: bool = True,
                                include_function_details: bool = True) -> bool:
        """
        导出函数调用关系到 JSON 文件
        
        Args:
            call_analyzer: 调用关系分析器
            output_file: 输出文件路径
            include_statistics: 是否包含统计信息
            include_function_details: 是否包含详细函数信息
            
        Returns:
            是否导出成功
        """
        try:
            # 获取调用关系数据
            relationships = call_analyzer.get_call_relationships()
            
            # 构建导出数据
            export_data = {
                'metadata': {
                    'tool_name': 'ElfScope',
                    'version': '1.0.0',
                    'export_time': datetime.now().isoformat(),
                    'elf_file': call_analyzer.elf_parser.filepath,
                    'architecture': call_analyzer.architecture
                },
                'functions': {},
                'call_relationships': []
            }
            
            # 添加函数信息
            if include_function_details:
                export_data['functions'] = self._format_functions(relationships['functions'])
            
            # 添加调用关系
            export_data['call_relationships'] = self._format_call_relationships(relationships['calls'])
            
            # 添加统计信息
            if include_statistics:
                export_data['statistics'] = call_analyzer.get_statistics()
            
            # 写入文件
            return self._write_json_file(export_data, output_file)
            
        except Exception as e:
            logging.error(f"导出调用关系时出错: {e}")
            return False
    
    def export_call_paths(self, 
                         path_finder: PathFinder,
                         target_function: str,
                         output_file: str,
                         source_function: Optional[str] = None,
                         max_depth: int = 10,
                         include_cycles: bool = False) -> bool:
        """
        导出调用路径到 JSON 文件
        
        Args:
            path_finder: 路径查找器
            target_function: 目标函数
            source_function: 源函数（可选）
            output_file: 输出文件路径
            max_depth: 最大搜索深度
            include_cycles: 是否包含环
            
        Returns:
            是否导出成功
        """
        try:
            # 查找路径
            path_result = path_finder.find_paths(
                target_function=target_function,
                source_function=source_function,
                max_depth=max_depth,
                include_cycles=include_cycles
            )
            
            # 构建导出数据
            export_data = {
                'metadata': {
                    'tool_name': 'ElfScope',
                    'version': '1.0.0',
                    'export_time': datetime.now().isoformat(),
                    'elf_file': path_finder.call_analyzer.elf_parser.filepath,
                    'architecture': path_finder.call_analyzer.architecture,
                    'query': {
                        'target_function': target_function,
                        'source_function': source_function,
                        'max_depth': max_depth,
                        'include_cycles': include_cycles
                    }
                },
                'path_analysis': path_result
            }
            
            # 如果没有指定源函数，还可以添加调用者分析
            if not source_function:
                callers_info = path_finder.find_all_callers(target_function, max_depth)
                export_data['caller_analysis'] = callers_info
            
            # 写入文件
            return self._write_json_file(export_data, output_file)
            
        except Exception as e:
            logging.error(f"导出调用路径时出错: {e}")
            return False
    
    def export_complete_analysis(self, 
                               elf_parser: ElfParser,
                               call_analyzer: CallAnalyzer,
                               output_file: str) -> bool:
        """
        导出完整的分析结果
        
        Args:
            elf_parser: ELF解析器
            call_analyzer: 调用关系分析器
            output_file: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            # 获取各种分析数据
            relationships = call_analyzer.get_call_relationships()
            statistics = call_analyzer.get_statistics()
            file_info = elf_parser.get_file_info()
            
            # 构建完整导出数据
            export_data = {
                'metadata': {
                    'tool_name': 'ElfScope',
                    'version': '1.0.0',
                    'export_time': datetime.now().isoformat(),
                    'export_type': 'complete_analysis'
                },
                'elf_info': file_info,
                'analysis': {
                    'functions': self._format_functions(relationships['functions']),
                    'call_relationships': self._format_call_relationships(relationships['calls']),
                    'statistics': statistics
                }
            }
            
            # 添加架构特定信息
            text_sections = elf_parser.get_text_sections()
            export_data['elf_info']['text_sections'] = text_sections
            
            # 写入文件
            return self._write_json_file(export_data, output_file)
            
        except Exception as e:
            logging.error(f"导出完整分析时出错: {e}")
            return False
    
    def _format_functions(self, functions: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化函数信息
        
        Args:
            functions: 原始函数信息
            
        Returns:
            格式化后的函数信息
        """
        formatted = {}
        
        for name, func_data in functions.items():
            formatted[name] = {
                'name': name,
                'address': hex(func_data.get('value', 0)),
                'size': func_data.get('size', 0),
                'type': func_data.get('type', 'unknown'),
                'visibility': func_data.get('visibility', 'default'),
                'external': func_data.get('external', False)
            }
        
        return formatted
    
    def _format_call_relationships(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化调用关系信息
        
        Args:
            calls: 原始调用关系信息
            
        Returns:
            格式化后的调用关系信息
        """
        formatted = []
        
        for call in calls:
            formatted_call = {
                'from_function': call['from_function'],
                'to_function': call['to_function'],
                'from_address': hex(call['from_address']),
                'instruction': call['instruction'],
                'type': call['type']
            }
            
            if 'to_address' in call:
                formatted_call['to_address'] = hex(call['to_address'])
            
            if call.get('external', False):
                formatted_call['external'] = True
            
            formatted.append(formatted_call)
        
        return formatted
    
    def _write_json_file(self, data: Dict[str, Any], output_file: str) -> bool:
        """
        写入JSON文件
        
        Args:
            data: 要写入的数据
            output_file: 输出文件路径
            
        Returns:
            是否写入成功
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 写入JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, 
                         indent=self.default_indent,
                         ensure_ascii=self.ensure_ascii,
                         default=self._json_serializer)
            
            logging.info(f"成功导出到文件: {output_file}")
            return True
            
        except Exception as e:
            logging.error(f"写入JSON文件 {output_file} 时出错: {e}")
            return False
    
    def _json_serializer(self, obj):
        """
        JSON序列化器，处理特殊类型
        
        Args:
            obj: 要序列化的对象
            
        Returns:
            可序列化的对象
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def create_summary_report(self, 
                            elf_parser: ElfParser, 
                            call_analyzer: CallAnalyzer,
                            output_file: str) -> bool:
        """
        创建分析摘要报告
        
        Args:
            elf_parser: ELF解析器
            call_analyzer: 调用关系分析器
            output_file: 输出文件路径
            
        Returns:
            是否创建成功
        """
        try:
            file_info = elf_parser.get_file_info()
            statistics = call_analyzer.get_statistics()
            
            # 查找环
            cycles = call_analyzer.find_cycles()
            
            # 创建摘要数据
            summary = {
                'metadata': {
                    'tool_name': 'ElfScope',
                    'version': '1.0.0',
                    'report_time': datetime.now().isoformat(),
                    'report_type': 'summary'
                },
                'file_summary': {
                    'filepath': file_info['filepath'],
                    'architecture': file_info['architecture'],
                    'file_type': file_info['file_type'],
                    'entry_point': file_info['entry_point']
                },
                'analysis_summary': {
                    'total_functions': statistics['total_functions'],
                    'total_calls': statistics['total_calls'],
                    'external_functions': statistics['external_functions'],
                    'recursive_functions': statistics['recursive_functions'],
                    'call_cycles': len(cycles),
                    'average_calls_per_function': round(statistics['average_calls_per_function'], 2)
                },
                'notable_findings': {
                    'cycles': cycles[:10] if cycles else [],  # 限制显示的环数量
                    'has_recursion': statistics['recursive_functions'] > 0,
                    'complexity': self._assess_complexity(statistics)
                }
            }
            
            return self._write_json_file(summary, output_file)
            
        except Exception as e:
            logging.error(f"创建摘要报告时出错: {e}")
            return False
    
    def _assess_complexity(self, statistics: Dict[str, Any]) -> str:
        """
        评估代码复杂性
        
        Args:
            statistics: 统计信息
            
        Returns:
            复杂性评估结果
        """
        total_functions = statistics.get('total_functions', 0)
        total_calls = statistics.get('total_calls', 0)
        avg_calls = statistics.get('average_calls_per_function', 0.0)
        cycles = statistics.get('cycles', 0)
        
        if total_functions < 10:
            return 'simple'
        elif total_functions < 50 and avg_calls < 3:
            return 'moderate'
        elif total_functions < 200 and avg_calls < 5 and cycles < 5:
            return 'complex'
        else:
            return 'highly_complex'
    
    def export_function_details(self, 
                              call_analyzer: CallAnalyzer,
                              function_name: str,
                              output_file: str) -> bool:
        """
        导出特定函数的详细信息
        
        Args:
            call_analyzer: 调用关系分析器
            function_name: 函数名
            output_file: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            if function_name not in call_analyzer.call_graph:
                logging.error(f"函数 '{function_name}' 不存在")
                return False
            
            # 获取函数详细信息
            callers = call_analyzer.get_callers(function_name)
            callees = call_analyzer.get_callees(function_name)
            is_recursive = call_analyzer.is_recursive_function(function_name)
            depth = call_analyzer.get_function_depth(function_name)
            
            # 创建路径查找器
            path_finder = PathFinder(call_analyzer)
            reachability = path_finder.analyze_function_reachability(function_name)
            
            # 构建详细信息
            details = {
                'metadata': {
                    'tool_name': 'ElfScope',
                    'version': '1.0.0',
                    'export_time': datetime.now().isoformat(),
                    'elf_file': call_analyzer.elf_parser.filepath,
                    'target_function': function_name
                },
                'function_details': {
                    'name': function_name,
                    'callers': {
                        'count': len(callers),
                        'functions': callers
                    },
                    'callees': {
                        'count': len(callees),
                        'functions': callees
                    },
                    'properties': {
                        'is_recursive': is_recursive,
                        'call_depth': depth,
                        'is_leaf_function': len(callees) == 0,
                        'is_entry_function': len(callers) == 0
                    },
                    'reachability': reachability
                }
            }
            
            # 添加具体调用详情
            call_details = {}
            for callee in callees:
                call_details[callee] = call_analyzer.get_call_details(function_name, callee)
            
            details['function_details']['call_details'] = call_details
            
            return self._write_json_file(details, output_file)
            
        except Exception as e:
            logging.error(f"导出函数详情时出错: {e}")
            return False
    
    def export_data(self, data: Dict[str, Any], output_file: str) -> bool:
        """
        导出任意数据到 JSON 文件
        
        Args:
            data: 要导出的数据
            output_file: 输出文件路径
            
        Returns:
            导出是否成功
        """
        try:
            return self._write_json_file(data, output_file)
        except Exception as e:
            logging.error(f"导出数据时出错: {e}")
            return False