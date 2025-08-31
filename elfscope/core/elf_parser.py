"""
ELF 文件解析器模块

该模块提供 ELF 文件的解析功能，包括：
- ELF 头部信息解析
- 架构检测
- 符号表提取
- 节区信息提取
"""

import os
from typing import Dict, List, Optional, Tuple, Any
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.constants import SH_FLAGS
from elftools.common.exceptions import ELFError


class ElfParser:
    """
    ELF 文件解析器
    
    负责解析 ELF 文件的基础信息，包括架构、符号表、代码段等。
    """
    
    # 支持的架构映射
    ARCH_MAPPING = {
        'EM_X86_64': 'x86_64',
        'EM_386': 'x86',
        'EM_ARM': 'arm',
        'EM_AARCH64': 'aarch64',
        'EM_MIPS': 'mips',
        'EM_PPC': 'ppc',
        'EM_PPC64': 'ppc64',
        'EM_RISCV': 'riscv'
    }
    
    def __init__(self, filepath: str):
        """
        初始化 ELF 解析器
        
        Args:
            filepath: ELF 文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ELFError: 不是有效的 ELF 文件
        """
        self.filepath = filepath
        self._validate_file()
        
        # 保持文件句柄打开
        self._file_handle = open(filepath, 'rb')
        self.elffile = ELFFile(self._file_handle)
        self._parse_basic_info()
    
    def _validate_file(self) -> None:
        """验证文件是否存在且可读"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"文件不存在: {self.filepath}")
        
        if not os.path.isfile(self.filepath):
            raise ValueError(f"路径不是文件: {self.filepath}")
        
        if not os.access(self.filepath, os.R_OK):
            raise PermissionError(f"文件不可读: {self.filepath}")
    
    def _parse_basic_info(self) -> None:
        """解析 ELF 文件的基础信息"""
        header = self.elffile.header
        
        # 获取架构信息
        self.machine = header['e_machine']
        self.arch = self.ARCH_MAPPING.get(self.machine, 'unknown')
        
        # 获取位数和字节序
        self.elfclass = header['e_ident']['EI_CLASS']  # ELFCLASS32 或 ELFCLASS64
        self.data = header['e_ident']['EI_DATA']  # ELFDATA2LSB 或 ELFDATA2MSB
        
        # 文件类型
        self.file_type = header['e_type']
        
        # 入口点
        self.entry_point = header['e_entry']
        
        # 解析节区信息
        self._parse_sections()
        
        # 解析符号表
        self._parse_symbols()
    
    def _parse_sections(self) -> None:
        """解析所有节区信息"""
        self.sections = {}
        self.text_sections = []  # 代码段
        
        for section in self.elffile.iter_sections():
            section_info = {
                'name': section.name,
                'type': section['sh_type'],
                'flags': section['sh_flags'],
                'addr': section['sh_addr'],
                'offset': section['sh_offset'],
                'size': section['sh_size'],
                'addralign': section['sh_addralign'],
                'entsize': section['sh_entsize']
            }
            
            self.sections[section.name] = section_info
            
            # 识别可执行段
            if (section['sh_flags'] & SH_FLAGS.SHF_EXECINSTR and 
                section['sh_size'] > 0):
                self.text_sections.append(section_info)
    
    def _parse_symbols(self) -> None:
        """解析符号表"""
        self.symbols = []
        self.function_symbols = []
        
        for section in self.elffile.iter_sections():
            if isinstance(section, SymbolTableSection):
                for symbol in section.iter_symbols():
                    symbol_info = {
                        'name': symbol.name,
                        'value': symbol['st_value'],
                        'size': symbol['st_size'],
                        'type': symbol['st_info']['type'],
                        'bind': symbol['st_info']['bind'],
                        'visibility': symbol['st_other']['visibility'],
                        'shndx': symbol['st_shndx']
                    }
                    
                    self.symbols.append(symbol_info)
                    
                    # 收集函数符号
                    if (symbol_info['type'] == 'STT_FUNC' and 
                        symbol_info['size'] > 0):
                        self.function_symbols.append(symbol_info)
    
    def get_architecture(self) -> str:
        """
        获取文件架构
        
        Returns:
            架构名称字符串
        """
        return self.arch
    
    def get_entry_point(self) -> int:
        """
        获取程序入口点
        
        Returns:
            入口点地址
        """
        return self.entry_point
    
    def get_text_sections(self) -> List[Dict[str, Any]]:
        """
        获取所有代码段信息
        
        Returns:
            代码段信息列表
        """
        return self.text_sections.copy()
    
    def get_functions(self) -> List[Dict[str, Any]]:
        """
        获取所有函数符号
        
        Returns:
            函数符号信息列表
        """
        return self.function_symbols.copy()
    
    def get_function_by_address(self, address: int) -> Optional[Dict[str, Any]]:
        """
        根据地址查找函数
        
        Args:
            address: 目标地址
            
        Returns:
            函数信息字典，如果没找到则返回 None
        """
        for func in self.function_symbols:
            start_addr = func['value']
            end_addr = start_addr + func['size']
            
            if start_addr <= address < end_addr:
                return func
        
        return None
    
    def get_function_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称查找函数
        
        Args:
            name: 函数名称
            
        Returns:
            函数信息字典，如果没找到则返回 None
        """
        for func in self.function_symbols:
            if func['name'] == name:
                return func
        
        return None
    
    def get_section_data(self, section_name: str) -> Optional[bytes]:
        """
        获取指定节区的数据
        
        Args:
            section_name: 节区名称
            
        Returns:
            节区数据，如果不存在则返回 None
        """
        section = self.elffile.get_section_by_name(section_name)
        if section:
            return section.data()
        return None
    
    def is_executable(self) -> bool:
        """
        检查文件是否为可执行文件
        
        Returns:
            是否为可执行文件
        """
        return self.file_type == 'ET_EXEC'
    
    def is_shared_library(self) -> bool:
        """
        检查文件是否为共享库
        
        Returns:
            是否为共享库
        """
        return self.file_type == 'ET_DYN'
    
    def get_file_info(self) -> Dict[str, Any]:
        """
        获取文件的完整信息摘要
        
        Returns:
            包含文件所有基础信息的字典
        """
        return {
            'filepath': self.filepath,
            'architecture': self.arch,
            'machine': self.machine,
            'elfclass': self.elfclass,
            'data': self.data,
            'file_type': self.file_type,
            'entry_point': hex(self.entry_point),
            'num_sections': len(self.sections),
            'num_symbols': len(self.symbols),
            'num_functions': len(self.function_symbols),
            'text_sections': len(self.text_sections)
        }
    
    def close(self):
        """关闭文件句柄"""
        if hasattr(self, '_file_handle') and self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    def __del__(self):
        """析构时清理资源"""
        self.close()
