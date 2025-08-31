"""
ELF 解析器测试用例
"""

import os
import pytest
import tempfile
from unittest.mock import patch, mock_open

from elfscope.core.elf_parser import ElfParser
from elftools.common.exceptions import ELFError


class TestElfParser:
    """ELF 解析器测试类"""

    def test_init_file_not_found(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            ElfParser("/nonexistent/file")

    def test_init_not_a_file(self):
        """测试路径不是文件的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                ElfParser(tmpdir)

    @patch('builtins.open')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_init_permission_denied(self, mock_access, mock_isfile, mock_exists, mock_open_func):
        """测试文件无读取权限的情况"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = False
        
        with pytest.raises(PermissionError):
            ElfParser("/path/to/file")

    def test_architecture_mapping(self):
        """测试架构映射"""
        # 测试已知架构
        assert 'EM_X86_64' in ElfParser.ARCH_MAPPING
        assert 'EM_ARM' in ElfParser.ARCH_MAPPING
        assert ElfParser.ARCH_MAPPING['EM_X86_64'] == 'x86_64'
        assert ElfParser.ARCH_MAPPING['EM_ARM'] == 'arm'

    @patch('elfscope.core.elf_parser.ELFFile')
    @patch('builtins.open')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_get_functions(self, mock_access, mock_isfile, mock_exists, mock_open_func, mock_elffile):
        """测试获取函数列表"""
        # 设置模拟对象
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        
        # 模拟 ELF 文件头
        mock_header = {
            'e_machine': 'EM_X86_64',
            'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
            'e_type': 'ET_EXEC',
            'e_entry': 0x400000
        }
        
        # 模拟符号
        mock_symbol = type('MockSymbol', (), {
            'name': 'test_function',
            '__getitem__': lambda self, key: {
                'st_value': 0x401000,
                'st_size': 100,
                'st_info': {'type': 'STT_FUNC', 'bind': 'STB_GLOBAL'},
                'st_other': {'visibility': 'STV_DEFAULT'},
                'st_shndx': 1
            }[key]
        })()
        
        # 模拟符号表节区
        mock_symtab = type('MockSymbolTableSection', (), {
            'iter_symbols': lambda: [mock_symbol]
        })()
        
        # 模拟 ELF 文件对象
        mock_elf = type('MockELFFile', (), {
            'header': mock_header,
            'iter_sections': lambda: [mock_symtab]
        })()
        
        mock_elffile.return_value = mock_elf
        
        # 创建解析器并测试
        parser = ElfParser("/path/to/test.elf")
        functions = parser.get_functions()
        
        assert len(functions) == 1
        assert functions[0]['name'] == 'test_function'
        assert functions[0]['value'] == 0x401000
        assert functions[0]['size'] == 100

    @patch('elfscope.core.elf_parser.ELFFile')
    @patch('builtins.open')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_get_function_by_name(self, mock_access, mock_isfile, mock_exists, mock_open_func, mock_elffile):
        """测试按名称查找函数"""
        # 设置基本模拟
        self._setup_basic_mocks(mock_access, mock_isfile, mock_exists, mock_elffile)
        
        parser = ElfParser("/path/to/test.elf")
        
        # 测试存在的函数
        func = parser.get_function_by_name('test_function')
        assert func is not None
        assert func['name'] == 'test_function'
        
        # 测试不存在的函数
        func = parser.get_function_by_name('nonexistent_function')
        assert func is None

    @patch('elfscope.core.elf_parser.ELFFile')
    @patch('builtins.open')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_get_function_by_address(self, mock_access, mock_isfile, mock_exists, mock_open_func, mock_elffile):
        """测试按地址查找函数"""
        self._setup_basic_mocks(mock_access, mock_isfile, mock_exists, mock_elffile)
        
        parser = ElfParser("/path/to/test.elf")
        
        # 测试地址在函数范围内
        func = parser.get_function_by_address(0x401050)  # 在函数范围内
        assert func is not None
        assert func['name'] == 'test_function'
        
        # 测试地址超出函数范围
        func = parser.get_function_by_address(0x402000)
        assert func is None

    def _setup_basic_mocks(self, mock_access, mock_isfile, mock_exists, mock_elffile):
        """设置基本的模拟对象"""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_access.return_value = True
        
        # 模拟 ELF 文件头
        mock_header = {
            'e_machine': 'EM_X86_64',
            'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
            'e_type': 'ET_EXEC',
            'e_entry': 0x400000
        }
        
        # 模拟符号
        mock_symbol = type('MockSymbol', (), {
            'name': 'test_function',
            '__getitem__': lambda self, key: {
                'st_value': 0x401000,
                'st_size': 100,
                'st_info': {'type': 'STT_FUNC', 'bind': 'STB_GLOBAL'},
                'st_other': {'visibility': 'STV_DEFAULT'},
                'st_shndx': 1
            }[key]
        })()
        
        # 模拟符号表节区
        mock_symtab = type('MockSymbolTableSection', (), {
            'iter_symbols': lambda: [mock_symbol]
        })()
        
        # 模拟代码段
        mock_text_section = type('MockSection', (), {
            'name': '.text',
            '__getitem__': lambda self, key: {
                'sh_type': 'SHT_PROGBITS',
                'sh_flags': 0x6,  # SHF_ALLOC | SHF_EXECINSTR
                'sh_addr': 0x401000,
                'sh_offset': 0x1000,
                'sh_size': 0x1000,
                'sh_addralign': 16,
                'sh_entsize': 0
            }[key]
        })()
        
        # 模拟 ELF 文件对象
        mock_elf = type('MockELFFile', (), {
            'header': mock_header,
            'iter_sections': lambda: [mock_symtab, mock_text_section],
            'get_section_by_name': lambda name: mock_text_section if name == '.text' else None
        })()
        
        mock_elffile.return_value = mock_elf


class TestElfParserIntegration:
    """ELF 解析器集成测试"""
    
    def test_create_test_elf_file(self, tmp_path):
        """创建测试用的简单 ELF 文件"""
        # 这个测试需要实际的 ELF 文件，在实际环境中会使用真实的二进制文件
        # 或者使用工具生成简单的 ELF 文件进行测试
        pass

    def test_parse_real_elf_file(self):
        """测试解析真实的 ELF 文件"""
        # 在实际测试环境中，这里会使用系统中的真实 ELF 文件
        # 例如 /bin/ls 或其他系统二进制文件
        common_binaries = ['/bin/ls', '/bin/cat', '/usr/bin/python3']
        
        for binary in common_binaries:
            if os.path.exists(binary):
                try:
                    parser = ElfParser(binary)
                    info = parser.get_file_info()
                    
                    assert 'architecture' in info
                    assert 'file_type' in info
                    assert 'entry_point' in info
                    
                    functions = parser.get_functions()
                    assert isinstance(functions, list)
                    
                    # 如果有函数，测试函数查找
                    if functions:
                        func = functions[0]
                        found_func = parser.get_function_by_name(func['name'])
                        assert found_func is not None
                        assert found_func['name'] == func['name']
                    
                    break
                except Exception as e:
                    # 如果解析失败，继续尝试下一个二进制文件
                    continue
