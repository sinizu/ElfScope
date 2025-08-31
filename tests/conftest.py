"""
pytest 配置和共享 fixtures
"""

import os
import tempfile
import shutil
import pytest
from unittest.mock import Mock


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_elf_path():
    """提供示例 ELF 文件路径"""
    # 在真实测试环境中，这里会提供一个测试用的 ELF 文件
    # 目前返回一个可能存在的系统二进制文件
    test_binaries = ['/bin/echo', '/bin/cat', '/usr/bin/env', '/bin/ls']
    
    for binary in test_binaries:
        if os.path.exists(binary) and os.access(binary, os.R_OK):
            return binary
    
    return None


@pytest.fixture
def mock_elf_data():
    """提供模拟的 ELF 数据"""
    return {
        'header': {
            'e_machine': 'EM_X86_64',
            'e_ident': {'EI_CLASS': 'ELFCLASS64', 'EI_DATA': 'ELFDATA2LSB'},
            'e_type': 'ET_EXEC',
            'e_entry': 0x401000
        },
        'functions': [
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
            },
            {
                'name': 'utility_func',
                'value': 0x401200,
                'size': 30,
                'type': 'STT_FUNC'
            }
        ],
        'calls': [
            {
                'from_function': 'main',
                'to_function': 'helper_func',
                'from_address': 0x401010,
                'to_address': 0x401100,
                'instruction': 'call 0x401100',
                'type': 'call'
            },
            {
                'from_function': 'helper_func',
                'to_function': 'utility_func',
                'from_address': 0x401110,
                'to_address': 0x401200,
                'instruction': 'call 0x401200',
                'type': 'call'
            }
        ]
    }


def pytest_configure(config):
    """pytest 配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_elf: marks tests that require real ELF files"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    if config.getoption("--lf") or config.getoption("--ff"):
        # 如果使用了 --lf 或 --ff 选项，不做额外处理
        return
    
    # 为没有明确标记的测试添加 'unit' 标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "fixtures")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    return data_dir


class MockElfBuilder:
    """构建模拟 ELF 对象的辅助类"""
    
    @staticmethod
    def create_mock_symbol(name, value, size, symbol_type='STT_FUNC'):
        """创建模拟符号"""
        symbol = Mock()
        symbol.name = name
        symbol.__getitem__ = Mock(return_value={
            'st_value': value,
            'st_size': size,
            'st_info': {'type': symbol_type, 'bind': 'STB_GLOBAL'},
            'st_other': {'visibility': 'STV_DEFAULT'},
            'st_shndx': 1
        })
        return symbol
    
    @staticmethod
    def create_mock_section(name, addr, size, section_type='SHT_PROGBITS', flags=0x6):
        """创建模拟节区"""
        section = Mock()
        section.name = name
        section.__getitem__ = Mock(return_value={
            'sh_type': section_type,
            'sh_flags': flags,
            'sh_addr': addr,
            'sh_offset': addr - 0x400000 + 0x1000,  # 模拟偏移
            'sh_size': size,
            'sh_addralign': 16,
            'sh_entsize': 0
        })
        section.data = Mock(return_value=b'\x90' * size)
        return section


@pytest.fixture
def mock_elf_builder():
    """提供 MockElfBuilder 实例"""
    return MockElfBuilder()
