"""
调用关系分析器测试用例
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from elfscope.core.call_analyzer import CallAnalyzer
from elfscope.core.elf_parser import ElfParser


class TestCallAnalyzer:
    """调用关系分析器测试类"""

    @pytest.fixture
    def mock_elf_parser(self):
        """创建模拟的 ELF 解析器"""
        parser = Mock(spec=ElfParser)
        parser.filepath = "/test/binary"
        parser.get_architecture.return_value = "x86_64"
        parser.get_functions.return_value = [
            {
                'name': 'main',
                'value': 0x401000,
                'size': 100,
                'type': 'STT_FUNC'
            },
            {
                'name': 'helper_func',
                'value': 0x401100,
                'size': 50,
                'type': 'STT_FUNC'
            }
        ]
        parser.get_text_sections.return_value = [
            {
                'name': '.text',
                'addr': 0x401000,
                'size': 0x1000,
                'offset': 0x1000
            }
        ]
        parser.get_section_data.return_value = b'\x90' * 0x1000  # NOP 指令
        parser.get_function_by_address.return_value = None
        
        return parser

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_init(self, mock_disassembler_class, mock_elf_parser):
        """测试初始化"""
        mock_disassembler = Mock()
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        
        assert analyzer.elf_parser == mock_elf_parser
        assert analyzer.architecture == "x86_64"
        assert not analyzer.analyzed
        assert 'main' in analyzer.name_to_function
        assert 'helper_func' in analyzer.name_to_function

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_analyze(self, mock_disassembler_class, mock_elf_parser):
        """测试分析过程"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = [
            {
                'from_address': 0x401010,
                'to_address': 0x401100,
                'instruction': 'call 0x401100',
                'type': 'call'
            }
        ]
        mock_disassembler_class.return_value = mock_disassembler
        
        # 设置 get_function_by_address 返回目标函数
        def mock_get_function_by_address(addr):
            if addr == 0x401100:
                return {'name': 'helper_func', 'value': 0x401100}
            return None
        
        mock_elf_parser.get_function_by_address.side_effect = mock_get_function_by_address
        
        analyzer = CallAnalyzer(mock_elf_parser)
        analyzer.analyze()
        
        assert analyzer.analyzed
        assert len(analyzer.function_calls) > 0
        assert 'main' in analyzer.function_calls or 'helper_func' in analyzer.function_calls

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_get_call_relationships(self, mock_disassembler_class, mock_elf_parser):
        """测试获取调用关系"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = []
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        relationships = analyzer.get_call_relationships()
        
        assert 'functions' in relationships
        assert 'calls' in relationships
        assert 'statistics' in relationships
        assert relationships['statistics']['total_functions'] == 2

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_get_callers_and_callees(self, mock_disassembler_class, mock_elf_parser):
        """测试获取调用者和被调用者"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = []
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        analyzer.analyze()
        
        # 手动添加一个调用关系用于测试
        analyzer.call_graph.add_edge('main', 'helper_func')
        
        callers = analyzer.get_callers('helper_func')
        callees = analyzer.get_callees('main')
        
        assert 'main' in callers
        assert 'helper_func' in callees

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_is_recursive_function(self, mock_disassembler_class, mock_elf_parser):
        """测试递归函数检测"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = []
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        analyzer.analyze()
        
        # 添加自我调用边
        analyzer.call_graph.add_edge('main', 'main')
        
        assert analyzer.is_recursive_function('main')
        assert not analyzer.is_recursive_function('helper_func')

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_find_cycles(self, mock_disassembler_class, mock_elf_parser):
        """测试环检测"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = []
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        analyzer.analyze()
        
        # 创建一个环：main -> helper_func -> main
        analyzer.call_graph.add_edge('main', 'helper_func')
        analyzer.call_graph.add_edge('helper_func', 'main')
        
        cycles = analyzer.find_cycles()
        
        # 应该检测到至少一个环
        assert len(cycles) > 0

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_get_statistics(self, mock_disassembler_class, mock_elf_parser):
        """测试统计信息"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = []
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        analyzer.analyze()
        
        stats = analyzer.get_statistics()
        
        required_keys = [
            'total_functions', 'total_calls', 'average_calls_per_function',
            'max_calls_from_function', 'max_calls_to_function',
            'recursive_functions', 'external_functions', 'cycles'
        ]
        
        for key in required_keys:
            assert key in stats
        
        assert stats['total_functions'] == 2
        assert isinstance(stats['total_calls'], int)
        assert isinstance(stats['average_calls_per_function'], (int, float))

    @patch('elfscope.core.call_analyzer.Disassembler')
    def test_external_function_handling(self, mock_disassembler_class, mock_elf_parser):
        """测试外部函数处理"""
        mock_disassembler = Mock()
        mock_disassembler.analyze_function_calls.return_value = [
            {
                'from_address': 0x401010,
                'to_address': 0x7fff12345678,  # 外部地址
                'instruction': 'call 0x7fff12345678',
                'type': 'call'
            }
        ]
        mock_disassembler_class.return_value = mock_disassembler
        
        analyzer = CallAnalyzer(mock_elf_parser)
        analyzer.analyze()
        
        # 检查是否正确处理了外部调用
        relationships = analyzer.get_call_relationships()
        external_calls = [call for call in relationships['calls'] if call.get('external', False)]
        
        assert len(external_calls) > 0
        assert external_calls[0]['to_function'].startswith('external_')


class TestCallAnalyzerIntegration:
    """调用关系分析器集成测试"""
    
    def test_analyze_with_real_disassembler(self):
        """测试使用真实反汇编器的分析"""
        # 这个测试需要真实的 ELF 文件和反汇编环境
        # 在实际测试环境中会使用真实的二进制文件
        pass

    def test_complex_call_graph(self):
        """测试复杂调用图的分析"""
        # 这个测试会创建更复杂的调用关系图
        # 包含多层调用、递归调用等情况
        pass
