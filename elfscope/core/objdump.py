"""
objdump 功能模块

该模块提供类似 GNU objdump 的功能，包括：
- 反汇编代码段
- 显示符号表
- 显示节区头信息
- 显示完整节区内容
- 显示重定位信息
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import Relocation, RelocationSection

from .elf_parser import ElfParser
from .disassembler import Disassembler, DisassemblerError


class ObjdumpAnalyzer:
    """
    objdump 分析器
    
    提供类似 GNU objdump 的功能，用于查看 ELF 文件的各种信息
    """
    
    def __init__(self, elf_parser: ElfParser):
        """
        初始化 objdump 分析器
        
        Args:
            elf_parser: ELF 解析器实例
        """
        self.elf_parser = elf_parser
        self.architecture = elf_parser.get_architecture()
        
        try:
            self.disassembler = Disassembler(self.architecture)
        except DisassemblerError as e:
            raise ValueError(f"无法初始化反汇编器: {e}")
        
        # 构建地址到函数名的映射
        self._build_function_map()
    
    def _build_function_map(self) -> None:
        """构建地址到函数名的映射"""
        self.addr_to_func = {}
        functions = self.elf_parser.get_functions()
        
        for func in functions:
            addr = func['value']
            name = func['name']
            if addr > 0 and name:
                self.addr_to_func[addr] = name
    
    def disassemble_section(self, 
                           section_name: Optional[str] = None,
                           start_address: Optional[int] = None,
                           end_address: Optional[int] = None) -> Dict[str, Any]:
        """
        反汇编指定节区或地址范围
        
        Args:
            section_name: 节区名称，如果为 None 则反汇编所有代码段
            start_address: 起始地址（十六进制字符串或整数）
            end_address: 结束地址（十六进制字符串或整数）
            
        Returns:
            包含反汇编结果的字典
        """
        result = {
            'sections': [],
            'total_instructions': 0
        }
        
        # 处理地址范围反汇编
        if start_address is not None:
            return self._disassemble_address_range(start_address, end_address)
        
        # 处理节区反汇编
        if section_name:
            sections = [s for s in self.elf_parser.text_sections if s['name'] == section_name]
            if not sections:
                raise ValueError(f"节区 '{section_name}' 不存在或不是代码段")
        else:
            sections = self.elf_parser.text_sections
        
        for section_info in sections:
            section_name = section_info['name']
            section_data = self.elf_parser.get_section_data(section_name)
            
            if not section_data:
                continue
            
            section_addr = section_info['addr']
            instructions = []
            
            try:
                # 使用反汇编器反汇编整个节区
                for insn in self.disassembler.disassemble(section_data, section_addr):
                    instruction_info = {
                        'address': insn.address,
                        'mnemonic': insn.mnemonic,
                        'op_str': insn.op_str,
                        'bytes': insn.bytes.hex(),
                        'size': insn.size
                    }
                    
                    # 检查是否是函数入口
                    if insn.address in self.addr_to_func:
                        instruction_info['function'] = self.addr_to_func[insn.address]
                    
                    # 检查是否是调用指令并解析目标
                    if self.disassembler.is_call_instruction(insn):
                        target = self.disassembler.extract_call_target(insn)
                        if target:
                            instruction_info['call_target'] = target
                            if target in self.addr_to_func:
                                instruction_info['call_target_name'] = self.addr_to_func[target]
                    
                    instructions.append(instruction_info)
                
                result['sections'].append({
                    'name': section_name,
                    'address': hex(section_addr),
                    'size': section_info['size'],
                    'instructions': instructions,
                    'instruction_count': len(instructions)
                })
                result['total_instructions'] += len(instructions)
                
            except Exception as e:
                logging.warning(f"反汇编节区 {section_name} 时出错: {e}")
                continue
        
        return result
    
    def _disassemble_address_range(self, 
                                   start_address: int,
                                   end_address: Optional[int] = None) -> Dict[str, Any]:
        """
        反汇编指定地址范围
        
        Args:
            start_address: 起始地址
            end_address: 结束地址，如果为 None 则只反汇编一个函数
            
        Returns:
            反汇编结果
        """
        # 转换地址格式
        if isinstance(start_address, str):
            start_address = int(start_address, 16)
        if isinstance(end_address, str):
            end_address = int(end_address, 16) if end_address else None
        
        # 找到包含该地址的节区
        section_data = None
        section_base = 0
        section_name = None
        
        for section in self.elf_parser.text_sections:
            section_addr = section['addr']
            section_end = section_addr + section['size']
            
            if section_addr <= start_address < section_end:
                section_name = section['name']
                section_base = section_addr
                section_data = self.elf_parser.get_section_data(section_name)
                break
        
        if not section_data:
            raise ValueError(f"地址 {hex(start_address)} 不在任何代码段中")
        
        # 计算节区内的偏移
        offset = start_address - section_base
        
        # 确定要反汇编的长度
        if end_address:
            length = end_address - start_address
        else:
            # 尝试找到函数边界
            func = self.elf_parser.get_function_by_address(start_address)
            if func:
                length = func['size']
            else:
                # 默认反汇编 100 字节
                length = min(100, len(section_data) - offset)
        
        # 提取要反汇编的数据
        data_to_disassemble = section_data[offset:offset + length]
        
        instructions = []
        for insn in self.disassembler.disassemble(data_to_disassemble, start_address):
            instruction_info = {
                'address': insn.address,
                'mnemonic': insn.mnemonic,
                'op_str': insn.op_str,
                'bytes': insn.bytes.hex(),
                'size': insn.size
            }
            
            # 检查是否是函数入口
            if insn.address in self.addr_to_func:
                instruction_info['function'] = self.addr_to_func[insn.address]
            
            # 检查调用目标
            if self.disassembler.is_call_instruction(insn):
                target = self.disassembler.extract_call_target(insn)
                if target:
                    instruction_info['call_target'] = target
                    if target in self.addr_to_func:
                        instruction_info['call_target_name'] = self.addr_to_func[target]
            
            instructions.append(instruction_info)
            
            # 如果达到结束地址，停止
            if end_address and insn.address >= end_address:
                break
        
        return {
            'address_range': {
                'start': hex(start_address),
                'end': hex(end_address) if end_address else None
            },
            'section': section_name,
            'instructions': instructions,
            'instruction_count': len(instructions)
        }
    
    def disassemble_function(self, function_name: str) -> Dict[str, Any]:
        """
        反汇编指定函数
        
        Args:
            function_name: 函数名称
            
        Returns:
            包含函数反汇编结果的字典
        """
        func = self.elf_parser.get_function_by_name(function_name)
        if not func:
            raise ValueError(f"函数 '{function_name}' 不存在")
        
        func_addr = func['value']
        func_size = func['size']
        
        # 找到包含该函数的节区
        section_data = None
        section_base = 0
        section_name = None
        
        for section in self.elf_parser.text_sections:
            section_addr = section['addr']
            section_end = section_addr + section['size']
            
            if section_addr <= func_addr < section_end:
                section_name = section['name']
                section_base = section_addr
                section_data = self.elf_parser.get_section_data(section_name)
                break
        
        if not section_data:
            raise ValueError(f"无法找到函数 '{function_name}' 所在的代码段")
        
        # 计算函数在节区中的偏移
        offset = func_addr - section_base
        func_bytes = section_data[offset:offset + func_size]
        
        instructions = []
        for insn in self.disassembler.disassemble(func_bytes, func_addr):
            instruction_info = {
                'address': insn.address,
                'mnemonic': insn.mnemonic,
                'op_str': insn.op_str,
                'bytes': insn.bytes.hex(),
                'size': insn.size
            }
            
            # 检查调用目标
            if self.disassembler.is_call_instruction(insn):
                target = self.disassembler.extract_call_target(insn)
                if target:
                    instruction_info['call_target'] = target
                    if target in self.addr_to_func:
                        instruction_info['call_target_name'] = self.addr_to_func[target]
            
            instructions.append(instruction_info)
        
        return {
            'function': function_name,
            'address': hex(func_addr),
            'size': func_size,
            'instructions': instructions,
            'instruction_count': len(instructions)
        }
    
    def show_symbols(self, symbol_type: Optional[str] = None) -> Dict[str, Any]:
        """
        显示符号表
        
        Args:
            symbol_type: 符号类型过滤 ('function', 'object', 'file' 等)
            
        Returns:
            包含符号信息的字典
        """
        result = {
            'symbols': [],
            'total_count': 0
        }
        
        symbols = self.elf_parser.symbols
        
        # 符号类型映射
        type_map = {
            'STT_FUNC': 'function',
            'STT_OBJECT': 'object',
            'STT_FILE': 'file',
            'STT_SECTION': 'section',
            'STT_NOTYPE': 'notype'
        }
        
        for symbol in symbols:
            if symbol_type:
                sym_type = type_map.get(symbol['type'], 'unknown')
                if sym_type != symbol_type:
                    continue
            
            symbol_info = {
                'value': hex(symbol['value']),
                'name': symbol['name'],
                'type': type_map.get(symbol['type'], symbol['type']),
                'size': symbol['size'],
                'bind': symbol['bind'],
                'visibility': symbol['visibility'],
                'shndx': symbol['shndx']
            }
            
            result['symbols'].append(symbol_info)
            result['total_count'] += 1
        
        return result
    
    def show_headers(self) -> Dict[str, Any]:
        """
        显示节区头信息
        
        Returns:
            包含节区头信息的字典
        """
        result = {
            'sections': [],
            'total_count': len(self.elf_parser.sections)
        }
        
        for section_name, section_info in self.elf_parser.sections.items():
            header_info = {
                'name': section_name,
                'type': section_info['type'],
                'address': hex(section_info['addr']),
                'offset': hex(section_info['offset']),
                'size': section_info['size'],
                'flags': self._format_section_flags(section_info['flags']),
                'alignment': section_info['addralign'],
                'entry_size': section_info['entsize']
            }
            
            result['sections'].append(header_info)
        
        return result
    
    def _format_section_flags(self, flags: int) -> str:
        """
        格式化节区标志
        
        Args:
            flags: 节区标志值
            
        Returns:
            格式化的标志字符串
        """
        from elftools.elf.constants import SH_FLAGS
        
        flag_list = []
        if flags & SH_FLAGS.SHF_WRITE:
            flag_list.append('W')
        if flags & SH_FLAGS.SHF_ALLOC:
            flag_list.append('A')
        if flags & SH_FLAGS.SHF_EXECINSTR:
            flag_list.append('X')
        if flags & SH_FLAGS.SHF_MERGE:
            flag_list.append('M')
        if flags & SH_FLAGS.SHF_STRINGS:
            flag_list.append('S')
        if flags & SH_FLAGS.SHF_INFO_LINK:
            flag_list.append('I')
        if flags & SH_FLAGS.SHF_LINK_ORDER:
            flag_list.append('L')
        if flags & SH_FLAGS.SHF_OS_NONCONFORMING:
            flag_list.append('O')
        if flags & SH_FLAGS.SHF_GROUP:
            flag_list.append('G')
        if flags & SH_FLAGS.SHF_TLS:
            flag_list.append('T')
        
        return ''.join(flag_list) if flag_list else ''
    
    def show_full_contents(self, section_name: Optional[str] = None) -> Dict[str, Any]:
        """
        显示完整节区内容（十六进制 + ASCII）
        
        Args:
            section_name: 节区名称，如果为 None 则显示所有节区
            
        Returns:
            包含节区内容的字典
        """
        result = {
            'sections': []
        }
        
        sections_to_show = [section_name] if section_name else list(self.elf_parser.sections.keys())
        
        for sec_name in sections_to_show:
            section_data = self.elf_parser.get_section_data(sec_name)
            
            if section_data is None:
                continue
            
            section_info = self.elf_parser.sections.get(sec_name, {})
            section_addr = section_info.get('addr', 0)
            
            # 格式化内容为十六进制和 ASCII
            lines = []
            bytes_per_line = 16
            
            for i in range(0, len(section_data), bytes_per_line):
                chunk = section_data[i:i + bytes_per_line]
                address = section_addr + i
                
                # 十六进制表示
                hex_str = ' '.join(f'{b:02x}' for b in chunk)
                # 填充到固定宽度
                hex_str = hex_str.ljust(bytes_per_line * 3 - 1)
                
                # ASCII 表示
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                
                lines.append({
                    'address': hex(address),
                    'hex': hex_str,
                    'ascii': ascii_str
                })
            
            result['sections'].append({
                'name': sec_name,
                'address': hex(section_addr),
                'size': len(section_data),
                'lines': lines
            })
        
        return result
    
    def show_relocations(self, section_name: Optional[str] = None) -> Dict[str, Any]:
        """
        显示重定位信息
        
        Args:
            section_name: 节区名称，如果为 None 则显示所有重定位节区
            
        Returns:
            包含重定位信息的字典
        """
        result = {
            'relocations': []
        }
        
        for section in self.elf_parser.elffile.iter_sections():
            if not isinstance(section, RelocationSection):
                continue
            
            if section_name and section.name != section_name:
                continue
            
            reloc_info = {
                'section': section.name,
                'relocations': []
            }
            
            # 获取关联的符号表
            symtab = None
            if section['sh_link'] < len(list(self.elf_parser.elffile.iter_sections())):
                linked_section = list(self.elf_parser.elffile.iter_sections())[section['sh_link']]
                if isinstance(linked_section, SymbolTableSection):
                    symtab = linked_section
            
            for reloc in section.iter_relocations():
                reloc_entry = {
                    'offset': hex(reloc['r_offset']),
                    'info': hex(reloc['r_info']),
                    'type': reloc['r_info_type']
                }
                
                # 获取符号信息（如果有）
                if symtab:
                    sym_index = reloc['r_info_sym']
                    if sym_index < symtab.num_symbols():
                        symbol = symtab.get_symbol(sym_index)
                        reloc_entry['symbol'] = symbol.name
                        reloc_entry['symbol_value'] = hex(symbol['st_value'])
                
                reloc_info['relocations'].append(reloc_entry)
            
            if reloc_info['relocations']:
                result['relocations'].append(reloc_info)
        
        return result
    
    def format_disassembly(self, disassembly_data: Dict[str, Any], format_type: str = 'text') -> str:
        """
        格式化反汇编输出
        
        Args:
            disassembly_data: 反汇编数据
            format_type: 格式类型 ('text' 或 'json')
            
        Returns:
            格式化后的字符串
        """
        if format_type == 'text':
            return self._format_disassembly_text(disassembly_data)
        else:
            import json
            return json.dumps(disassembly_data, indent=2, ensure_ascii=False)
    
    def _format_address(self, address: Any) -> str:
        """
        格式化地址为字符串
        
        Args:
            address: 地址（可以是整数或十六进制字符串）
            
        Returns:
            格式化的地址字符串
        """
        if isinstance(address, int):
            # 根据架构确定地址宽度
            if self.architecture in ['x86_64', 'aarch64']:
                return f"{address:016x}"
            else:
                return f"{address:08x}"
        elif isinstance(address, str):
            # 如果是字符串，尝试解析
            try:
                addr_int = int(address, 16) if address.startswith('0x') else int(address, 16)
                if self.architecture in ['x86_64', 'aarch64']:
                    return f"{addr_int:016x}"
                else:
                    return f"{addr_int:08x}"
            except (ValueError, AttributeError):
                return address
        else:
            return str(address)
    
    def _format_disassembly_text(self, data: Dict[str, Any]) -> str:
        """
        格式化为文本输出（类似 objdump）
        
        Args:
            data: 反汇编数据
            
        Returns:
            格式化的文本字符串
        """
        lines = []
        
        # 处理节区反汇编
        if 'sections' in data:
            for section in data['sections']:
                lines.append(f"\n节区 {section['name']} 的反汇编：")
                # 计算结束地址
                start_addr_str = section['address']
                try:
                    start_addr = int(start_addr_str, 16) if isinstance(start_addr_str, str) else start_addr_str
                    end_addr = start_addr + section['size']
                    lines.append(f"地址范围: {self._format_address(start_addr)} - {self._format_address(end_addr)}")
                except (ValueError, TypeError):
                    lines.append(f"地址范围: {start_addr_str} - (计算失败)")
                lines.append("")
                
                for insn in section['instructions']:
                    addr_str = self._format_address(insn['address'])
                    
                    # 如果有函数标签
                    if 'function' in insn:
                        lines.append("")
                        lines.append(f"{addr_str} <{insn['function']}>:")
                    
                    # 格式化字节码（每两个字符一组，最多显示16个字节）
                    bytes_str = insn['bytes']
                    bytes_formatted = ' '.join([bytes_str[i:i+2] for i in range(0, min(16, len(bytes_str)), 2)])
                    
                    # 指令字符串
                    instruction_str = f"{insn['mnemonic']:8s} {insn['op_str']}"
                    
                    # 如果有调用目标名称
                    if 'call_target_name' in insn:
                        call_target_str = self._format_address(insn['call_target'])
                        instruction_str = instruction_str.replace(
                            call_target_str, 
                            f"<{insn['call_target_name']}>"
                        )
                    
                    line = f"  {addr_str}: {bytes_formatted:24s} {instruction_str}"
                    lines.append(line)
        
        # 处理函数反汇编
        elif 'function' in data:
            lines.append(f"\n函数 {data['function']} 的反汇编：")
            lines.append(f"地址: {data['address']}, 大小: {data['size']} 字节")
            lines.append("")
            
            for insn in data['instructions']:
                addr_str = self._format_address(insn['address'])
                
                bytes_str = insn['bytes']
                bytes_formatted = ' '.join([bytes_str[i:i+2] for i in range(0, min(16, len(bytes_str)), 2)])
                
                instruction_str = f"{insn['mnemonic']:8s} {insn['op_str']}"
                
                if 'call_target_name' in insn:
                    call_target_str = self._format_address(insn['call_target'])
                    instruction_str = instruction_str.replace(
                        call_target_str, 
                        f"<{insn['call_target_name']}>"
                    )
                
                line = f"  {addr_str}: {bytes_formatted:24s} {instruction_str}"
                lines.append(line)
        
        # 处理地址范围反汇编
        elif 'address_range' in data:
            addr_range = data['address_range']
            lines.append(f"\n地址范围反汇编：")
            lines.append(f"起始: {addr_range['start']}, 结束: {addr_range['end']}")
            lines.append("")
            
            for insn in data['instructions']:
                addr_str = self._format_address(insn['address'])
                
                bytes_str = insn['bytes']
                bytes_formatted = ' '.join([bytes_str[i:i+2] for i in range(0, min(16, len(bytes_str)), 2)])
                
                instruction_str = f"{insn['mnemonic']:8s} {insn['op_str']}"
                
                if 'call_target_name' in insn:
                    call_target_str = self._format_address(insn['call_target'])
                    instruction_str = instruction_str.replace(
                        call_target_str, 
                        f"<{insn['call_target_name']}>"
                    )
                
                line = f"  {addr_str}: {bytes_formatted:24s} {instruction_str}"
                lines.append(line)
        
        return '\n'.join(lines)

