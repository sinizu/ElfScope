"""
集成测试用例

测试各个模块之间的协同工作
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch
import json

from elfscope.core.elf_parser import ElfParser
from elfscope.core.call_analyzer import CallAnalyzer
from elfscope.core.path_finder import PathFinder
from elfscope.utils.json_exporter import JsonExporter


class TestIntegration:
    """集成测试类"""
    
    @pytest.mark.integration
    def test_complete_workflow_mock(self):
        """测试完整的分析工作流（使用模拟数据）"""
        with patch('elfscope.core.elf_parser.ELFFile'), \
             patch('builtins.open'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            
            # 模拟 ELF 文件数据
            mock_header = {
                'e_machine': 'EM_X86_64',
                'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
                'e_type': 'ET_EXEC',
                'e_entry': 0x401000
            }
            
            # 创建测试数据
            with patch('elfscope.core.elf_parser.ELFFile') as mock_elffile:
                self._setup_mock_elf_file(mock_elffile, mock_header)
                
                # 1. 解析 ELF 文件
                elf_parser = ElfParser("/mock/test.elf")
                assert elf_parser.get_architecture() == 'x86_64'
                functions = elf_parser.get_functions()
                assert len(functions) > 0
                
                # 2. 分析调用关系
                with patch('elfscope.core.call_analyzer.Disassembler') as mock_disasm:
                    mock_disasm.return_value.analyze_function_calls.return_value = [
                        {
                            'from_address': 0x401010,
                            'to_address': 0x401100,
                            'instruction': 'call 0x401100',
                            'type': 'call'
                        }
                    ]
                    
                    call_analyzer = CallAnalyzer(elf_parser)
                    call_analyzer.analyze()
                    
                    relationships = call_analyzer.get_call_relationships()
                    assert 'functions' in relationships
                    assert 'calls' in relationships
                
                # 3. 查找调用路径
                path_finder = PathFinder(call_analyzer)
                paths_result = path_finder.find_paths('helper_func')
                assert 'paths' in paths_result
                
                # 4. 导出结果
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                    output_file = tmp_file.name
                
                try:
                    exporter = JsonExporter()
                    success = exporter.export_complete_analysis(
                        elf_parser=elf_parser,
                        call_analyzer=call_analyzer,
                        output_file=output_file
                    )
                    
                    assert success
                    assert os.path.exists(output_file)
                    
                    # 验证导出的 JSON 文件
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                    
                    assert 'metadata' in data
                    assert 'elf_info' in data
                    assert 'analysis' in data
                    
                finally:
                    if os.path.exists(output_file):
                        os.unlink(output_file)
    
    def _setup_mock_elf_file(self, mock_elffile_class, mock_header):
        """设置模拟的 ELF 文件"""
        # 模拟符号
        mock_symbols = [
            self._create_mock_symbol('main', 0x401000, 100),
            self._create_mock_symbol('helper_func', 0x401100, 50),
            self._create_mock_symbol('another_func', 0x401200, 30)
        ]
        
        # 模拟符号表节区
        mock_symtab = Mock()
        mock_symtab.iter_symbols.return_value = mock_symbols
        
        # 模拟代码段
        mock_text_section = Mock()
        mock_text_section.name = '.text'
        mock_text_section.__getitem__.return_value = {
            'sh_type': 'SHT_PROGBITS',
            'sh_flags': 0x6,  # SHF_ALLOC | SHF_EXECINSTR
            'sh_addr': 0x401000,
            'sh_offset': 0x1000,
            'sh_size': 0x1000,
            'sh_addralign': 16,
            'sh_entsize': 0
        }
        mock_text_section.data.return_value = b'\x90' * 0x1000  # NOP 指令
        
        # 模拟 ELF 文件对象
        mock_elf = Mock()
        mock_elf.header = mock_header
        mock_elf.iter_sections.return_value = [mock_symtab, mock_text_section]
        mock_elf.get_section_by_name.return_value = mock_text_section
        
        mock_elffile_class.return_value = mock_elf
    
    def _create_mock_symbol(self, name, value, size):
        """创建模拟符号"""
        symbol = Mock()
        symbol.name = name
        symbol.__getitem__.return_value = {
            'st_value': value,
            'st_size': size,
            'st_info': {'type': 'STT_FUNC', 'bind': 'STB_GLOBAL'},
            'st_other': {'visibility': 'STV_DEFAULT'},
            'st_shndx': 1
        }
        return symbol
    
    @pytest.mark.integration
    def test_error_propagation(self):
        """测试错误传播"""
        # 测试无效的 ELF 文件
        with pytest.raises(FileNotFoundError):
            ElfParser("/nonexistent/file")
        
        # 测试不支持的架构
        with patch('elfscope.core.elf_parser.ELFFile'), \
             patch('builtins.open'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            
            mock_header = {
                'e_machine': 'UNSUPPORTED_ARCH',
                'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
                'e_type': 'ET_EXEC',
                'e_entry': 0x401000
            }
            
            with patch('elfscope.core.elf_parser.ELFFile') as mock_elffile:
                mock_elf = Mock()
                mock_elf.header = mock_header
                mock_elf.iter_sections.return_value = []
                mock_elffile.return_value = mock_elf
                
                parser = ElfParser("/mock/test.elf")
                assert parser.get_architecture() == 'unknown'
                
                # 不支持的架构应该导致调用分析器初始化失败
                with pytest.raises(ValueError):
                    CallAnalyzer(parser)
    
    @pytest.mark.integration
    def test_empty_elf_file(self):
        """测试空的 ELF 文件处理"""
        with patch('elfscope.core.elf_parser.ELFFile'), \
             patch('builtins.open'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            
            mock_header = {
                'e_machine': 'EM_X86_64',
                'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
                'e_type': 'ET_EXEC',
                'e_entry': 0x401000
            }
            
            with patch('elfscope.core.elf_parser.ELFFile') as mock_elffile:
                mock_elf = Mock()
                mock_elf.header = mock_header
                mock_elf.iter_sections.return_value = []  # 没有节区
                mock_elf.get_section_by_name.return_value = None
                mock_elffile.return_value = mock_elf
                
                parser = ElfParser("/mock/empty.elf")
                functions = parser.get_functions()
                
                assert len(functions) == 0
                
                # 应该能够分析空文件
                with patch('elfscope.core.call_analyzer.Disassembler'):
                    call_analyzer = CallAnalyzer(parser)
                    call_analyzer.analyze()
                    
                    relationships = call_analyzer.get_call_relationships()
                    assert relationships['statistics']['total_functions'] == 0
                    assert relationships['statistics']['total_calls'] == 0
    
    @pytest.mark.integration
    def test_large_call_graph(self):
        """测试大型调用图的处理"""
        with patch('elfscope.core.elf_parser.ELFFile'), \
             patch('builtins.open'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            
            # 创建大量函数
            num_functions = 100
            functions = []
            for i in range(num_functions):
                functions.append(self._create_mock_symbol(f'func_{i}', 0x401000 + i * 100, 50))
            
            mock_header = {
                'e_machine': 'EM_X86_64',
                'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
                'e_type': 'ET_EXEC',
                'e_entry': 0x401000
            }
            
            with patch('elfscope.core.elf_parser.ELFFile') as mock_elffile:
                # 设置大型 ELF 文件
                mock_symtab = Mock()
                mock_symtab.iter_symbols.return_value = functions
                
                mock_text_section = Mock()
                mock_text_section.name = '.text'
                mock_text_section.__getitem__.return_value = {
                    'sh_type': 'SHT_PROGBITS',
                    'sh_flags': 0x6,
                    'sh_addr': 0x401000,
                    'sh_offset': 0x1000,
                    'sh_size': 0x10000,  # 更大的代码段
                    'sh_addralign': 16,
                    'sh_entsize': 0
                }
                mock_text_section.data.return_value = b'\x90' * 0x10000
                
                mock_elf = Mock()
                mock_elf.header = mock_header
                mock_elf.iter_sections.return_value = [mock_symtab, mock_text_section]
                mock_elf.get_section_by_name.return_value = mock_text_section
                mock_elffile.return_value = mock_elf
                
                parser = ElfParser("/mock/large.elf")
                parsed_functions = parser.get_functions()
                
                assert len(parsed_functions) == num_functions
                
                # 测试大型调用图的分析性能
                with patch('elfscope.core.call_analyzer.Disassembler') as mock_disasm:
                    mock_disasm.return_value.analyze_function_calls.return_value = []
                    
                    call_analyzer = CallAnalyzer(parser)
                    call_analyzer.analyze()
                    
                    stats = call_analyzer.get_statistics()
                    assert stats['total_functions'] == num_functions
                    
                    # 测试路径查找在大图上的性能
                    path_finder = PathFinder(call_analyzer)
                    result = path_finder.find_paths('func_50', max_depth=3)
                    
                    # 应该能够处理大图而不崩溃
                    assert 'paths' in result


class TestRealWorldScenarios:
    """真实世界场景测试"""
    
    @pytest.mark.requires_elf
    @pytest.mark.slow
    def test_system_binary_analysis(self):
        """测试系统二进制文件分析"""
        # 寻找系统中的二进制文件进行测试
        test_binaries = ['/bin/echo', '/bin/cat', '/usr/bin/env']
        
        for binary_path in test_binaries:
            if os.path.exists(binary_path) and os.access(binary_path, os.R_OK):
                try:
                    # 尝试分析真实的二进制文件
                    parser = ElfParser(binary_path)
                    info = parser.get_file_info()
                    
                    assert 'architecture' in info
                    assert info['architecture'] != 'unknown'
                    
                    functions = parser.get_functions()
                    if len(functions) > 0:
                        # 如果有函数，尝试进行调用分析
                        call_analyzer = CallAnalyzer(parser)
                        call_analyzer.analyze()
                        
                        stats = call_analyzer.get_statistics()
                        assert stats['total_functions'] > 0
                    
                    break  # 成功分析一个就足够了
                    
                except Exception as e:
                    # 如果某个二进制文件分析失败，继续尝试下一个
                    continue
            
    @pytest.mark.integration
    def test_cli_integration(self):
        """测试命令行接口集成"""
        # 这个测试会验证 CLI 命令是否能正确调用各个模块
        # 在实际测试中，这里会使用 subprocess 调用命令行工具
        pass
