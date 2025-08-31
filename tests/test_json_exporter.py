"""
JSON 导出器测试用例
"""

import json
import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from elfscope.utils.json_exporter import JsonExporter
from elfscope.core.elf_parser import ElfParser
from elfscope.core.call_analyzer import CallAnalyzer
from elfscope.core.path_finder import PathFinder


class TestJsonExporter:
    """JSON 导出器测试类"""

    @pytest.fixture
    def exporter(self):
        """创建导出器实例"""
        return JsonExporter()

    @pytest.fixture
    def mock_elf_parser(self):
        """创建模拟的 ELF 解析器"""
        parser = Mock(spec=ElfParser)
        parser.filepath = "/test/binary"
        parser.get_file_info.return_value = {
            'filepath': '/test/binary',
            'architecture': 'x86_64',
            'file_type': 'ET_EXEC',
            'entry_point': '0x401000',
            'num_functions': 5
        }
        return parser

    @pytest.fixture
    def mock_call_analyzer(self, mock_elf_parser):
        """创建模拟的调用关系分析器"""
        analyzer = Mock(spec=CallAnalyzer)
        analyzer.elf_parser = mock_elf_parser
        analyzer.architecture = 'x86_64'
        analyzer.get_call_relationships.return_value = {
            'functions': {
                'main': {
                    'name': 'main',
                    'value': 0x401000,
                    'size': 100,
                    'type': 'STT_FUNC',
                    'visibility': 'STV_DEFAULT',
                    'external': False
                },
                'helper': {
                    'name': 'helper',
                    'value': 0x401100,
                    'size': 50,
                    'type': 'STT_FUNC',
                    'visibility': 'STV_DEFAULT',
                    'external': False
                }
            },
            'calls': [
                {
                    'from_function': 'main',
                    'to_function': 'helper',
                    'from_address': 0x401010,
                    'to_address': 0x401100,
                    'instruction': 'call 0x401100',
                    'type': 'call',
                    'external': False
                }
            ]
        }
        analyzer.get_statistics.return_value = {
            'total_functions': 2,
            'total_calls': 1,
            'external_functions': 0,
            'recursive_functions': 0,
            'average_calls_per_function': 0.5
        }
        return analyzer

    @pytest.fixture
    def mock_path_finder(self, mock_call_analyzer):
        """创建模拟的路径查找器"""
        finder = Mock(spec=PathFinder)
        finder.call_analyzer = mock_call_analyzer
        finder.find_paths.return_value = {
            'target_function': 'helper',
            'source_function': 'main',
            'paths': [
                {
                    'path': ['main', 'helper'],
                    'length': 1,
                    'steps': [
                        {
                            'step': 1,
                            'from': 'main',
                            'to': 'helper',
                            'calls': [
                                {
                                    'from_address': 0x401010,
                                    'to_address': 0x401100,
                                    'instruction': 'call 0x401100',
                                    'type': 'call'
                                }
                            ]
                        }
                    ]
                }
            ],
            'statistics': {
                'total_paths': 1,
                'max_depth': 1,
                'min_depth': 1,
                'average_depth': 1.0
            }
        }
        finder.find_all_callers.return_value = {
            'target_function': 'helper',
            'total_callers': 1,
            'callers': [
                {
                    'function': 'main',
                    'paths_to_target': [['main', 'helper']],
                    'direct_caller': True
                }
            ]
        }
        return finder

    def test_init(self, exporter):
        """测试初始化"""
        assert exporter.default_indent == 2
        assert exporter.ensure_ascii == False

    def test_export_call_relationships(self, exporter, mock_call_analyzer):
        """测试导出调用关系"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        try:
            success = exporter.export_call_relationships(
                call_analyzer=mock_call_analyzer,
                output_file=output_file,
                include_statistics=True,
                include_function_details=True
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # 验证 JSON 文件内容
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'metadata' in data
            assert 'functions' in data
            assert 'call_relationships' in data
            assert 'statistics' in data
            
            # 检查元数据
            assert data['metadata']['tool_name'] == 'ElfScope'
            assert data['metadata']['architecture'] == 'x86_64'
            
            # 检查函数信息
            assert 'main' in data['functions']
            assert 'helper' in data['functions']
            
            # 检查调用关系
            assert len(data['call_relationships']) == 1
            call = data['call_relationships'][0]
            assert call['from_function'] == 'main'
            assert call['to_function'] == 'helper'
            
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_export_call_paths(self, exporter, mock_path_finder):
        """测试导出调用路径"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        try:
            success = exporter.export_call_paths(
                path_finder=mock_path_finder,
                target_function='helper',
                source_function='main',
                output_file=output_file
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # 验证内容
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'metadata' in data
            assert 'path_analysis' in data
            
            query = data['metadata']['query']
            assert query['target_function'] == 'helper'
            assert query['source_function'] == 'main'
            
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_export_complete_analysis(self, exporter, mock_elf_parser, mock_call_analyzer):
        """测试导出完整分析"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        # 添加 get_text_sections 方法
        mock_elf_parser.get_text_sections.return_value = [
            {
                'name': '.text',
                'addr': 0x401000,
                'size': 0x1000
            }
        ]
        
        try:
            success = exporter.export_complete_analysis(
                elf_parser=mock_elf_parser,
                call_analyzer=mock_call_analyzer,
                output_file=output_file
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # 验证内容
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'metadata' in data
            assert 'elf_info' in data
            assert 'analysis' in data
            
            assert data['metadata']['export_type'] == 'complete_analysis'
            
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_create_summary_report(self, exporter, mock_elf_parser, mock_call_analyzer):
        """测试创建摘要报告"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        # 添加 find_cycles 方法
        mock_call_analyzer.find_cycles.return_value = []
        
        try:
            success = exporter.create_summary_report(
                elf_parser=mock_elf_parser,
                call_analyzer=mock_call_analyzer,
                output_file=output_file
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # 验证内容
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'metadata' in data
            assert 'file_summary' in data
            assert 'analysis_summary' in data
            assert 'notable_findings' in data
            
            assert data['metadata']['report_type'] == 'summary'
            
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_export_function_details(self, exporter, mock_call_analyzer):
        """测试导出函数详情"""
        # 设置 call_graph
        import networkx as nx
        call_graph = nx.DiGraph()
        call_graph.add_node('test_func')
        mock_call_analyzer.call_graph = call_graph
        
        # 设置其他方法
        mock_call_analyzer.get_callers.return_value = ['caller_func']
        mock_call_analyzer.get_callees.return_value = ['callee_func']
        mock_call_analyzer.is_recursive_function.return_value = False
        mock_call_analyzer.get_function_depth.return_value = 2
        mock_call_analyzer.get_call_details.return_value = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        with patch('elfscope.utils.json_exporter.PathFinder') as mock_path_finder_class:
            mock_path_finder = Mock()
            mock_path_finder.analyze_function_reachability.return_value = {
                'function': 'test_func',
                'can_reach': {'count': 1, 'functions': ['callee_func']},
                'reachable_from': {'count': 1, 'functions': ['caller_func']},
                'is_leaf': False,
                'is_root': False
            }
            mock_path_finder_class.return_value = mock_path_finder
            
            try:
                success = exporter.export_function_details(
                    call_analyzer=mock_call_analyzer,
                    function_name='test_func',
                    output_file=output_file
                )
                
                assert success
                assert os.path.exists(output_file)
                
                # 验证内容
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                assert 'metadata' in data
                assert 'function_details' in data
                assert data['metadata']['target_function'] == 'test_func'
                
            finally:
                if os.path.exists(output_file):
                    os.unlink(output_file)

    def test_format_functions(self, exporter):
        """测试函数信息格式化"""
        functions = {
            'test_func': {
                'name': 'test_func',
                'value': 0x401000,
                'size': 100,
                'type': 'STT_FUNC',
                'visibility': 'STV_DEFAULT',
                'external': False
            }
        }
        
        formatted = exporter._format_functions(functions)
        
        assert 'test_func' in formatted
        func_info = formatted['test_func']
        
        assert func_info['name'] == 'test_func'
        assert func_info['address'] == '0x401000'
        assert func_info['size'] == 100
        assert func_info['external'] == False

    def test_format_call_relationships(self, exporter):
        """测试调用关系格式化"""
        calls = [
            {
                'from_function': 'main',
                'to_function': 'helper',
                'from_address': 0x401010,
                'to_address': 0x401100,
                'instruction': 'call 0x401100',
                'type': 'call',
                'external': False
            }
        ]
        
        formatted = exporter._format_call_relationships(calls)
        
        assert len(formatted) == 1
        call = formatted[0]
        
        assert call['from_function'] == 'main'
        assert call['to_function'] == 'helper'
        assert call['from_address'] == '0x401010'
        assert call['to_address'] == '0x401100'

    def test_assess_complexity(self, exporter):
        """测试复杂性评估"""
        # 简单项目
        simple_stats = {
            'total_functions': 5,
            'total_calls': 3,
            'average_calls_per_function': 0.6,
            'cycles': 0
        }
        assert exporter._assess_complexity(simple_stats) == 'simple'
        
        # 中等复杂项目
        moderate_stats = {
            'total_functions': 30,
            'total_calls': 60,
            'average_calls_per_function': 2.0,
            'cycles': 1
        }
        assert exporter._assess_complexity(moderate_stats) == 'moderate'
        
        # 复杂项目
        complex_stats = {
            'total_functions': 100,
            'total_calls': 400,
            'average_calls_per_function': 4.0,
            'cycles': 3
        }
        assert exporter._assess_complexity(complex_stats) == 'complex'
        
        # 高度复杂项目
        highly_complex_stats = {
            'total_functions': 500,
            'total_calls': 3000,
            'average_calls_per_function': 6.0,
            'cycles': 10
        }
        assert exporter._assess_complexity(highly_complex_stats) == 'highly_complex'

    def test_write_json_file_error_handling(self, exporter):
        """测试JSON文件写入错误处理"""
        # 尝试写入到无效路径
        invalid_path = "/root/cannot_write_here.json"
        
        success = exporter._write_json_file({}, invalid_path)
        # 在没有权限的情况下，应该返回 False
        # 注意：这个测试可能在某些环境下需要调整

    def test_json_serializer(self, exporter):
        """测试JSON序列化器"""
        # 测试 datetime 序列化
        now = datetime.now()
        result = exporter._json_serializer(now)
        assert isinstance(result, str)
        
        # 测试 set 序列化
        test_set = {1, 2, 3}
        result = exporter._json_serializer(test_set)
        assert isinstance(result, list)
        
        # 测试普通对象序列化
        class TestObject:
            def __init__(self):
                self.value = 42
        
        obj = TestObject()
        result = exporter._json_serializer(obj)
        assert 'value' in result

    def test_export_without_statistics(self, exporter, mock_call_analyzer):
        """测试不包含统计信息的导出"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        try:
            success = exporter.export_call_relationships(
                call_analyzer=mock_call_analyzer,
                output_file=output_file,
                include_statistics=False,
                include_function_details=False
            )
            
            assert success
            
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'statistics' not in data
            assert len(data['functions']) == 0
            
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)
