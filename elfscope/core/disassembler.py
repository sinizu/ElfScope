"""
反汇编模块

该模块提供多架构的反汇编功能，包括：
- 根据架构选择反汇编引擎
- 反汇编代码段
- 识别函数调用指令
- 提取调用目标地址
"""

from typing import Dict, List, Optional, Tuple, Generator, Any
import capstone
from elftools.elf.elffile import ELFFile


class DisassemblerError(Exception):
    """反汇编相关异常"""
    pass


class Disassembler:
    """
    多架构反汇编器
    
    支持多种架构的反汇编和调用指令识别
    """
    
    # 架构到 Capstone 架构的映射
    ARCH_MAPPING = {
        'x86_64': (capstone.CS_ARCH_X86, capstone.CS_MODE_64),
        'x86': (capstone.CS_ARCH_X86, capstone.CS_MODE_32),
        'arm': (capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM),
        'aarch64': (capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM),
        'mips': (capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32),
        'ppc': (capstone.CS_ARCH_PPC, capstone.CS_MODE_32),
        'ppc64': (capstone.CS_ARCH_PPC, capstone.CS_MODE_64),
    }
    
    # 调用指令助记符（按架构分类）
    CALL_INSTRUCTIONS = {
        'x86_64': {'call', 'callq'},
        'x86': {'call'},
        'arm': {'bl', 'blx'},
        'aarch64': {'bl', 'blr'},
        'mips': {'jal', 'jalr'},
        'ppc': {'bl', 'bla'},
        'ppc64': {'bl', 'bla'},
    }
    
    # 跳转指令助记符（可能是尾调用）
    JUMP_INSTRUCTIONS = {
        'x86_64': {'jmp', 'jmpq'},
        'x86': {'jmp'},
        'arm': {'b', 'bx'},
        'aarch64': {'b', 'br'},
        'mips': {'j', 'jr'},
        'ppc': {'b', 'ba'},
        'ppc64': {'b', 'ba'},
    }
    
    def __init__(self, architecture: str):
        """
        初始化反汇编器
        
        Args:
            architecture: 目标架构
            
        Raises:
            DisassemblerError: 不支持的架构
        """
        self.architecture = architecture
        
        if architecture not in self.ARCH_MAPPING:
            raise DisassemblerError(f"不支持的架构: {architecture}")
        
        arch, mode = self.ARCH_MAPPING[architecture]
        
        try:
            self.cs = capstone.Cs(arch, mode)
            self.cs.detail = True  # 开启详细信息
        except capstone.CsError as e:
            raise DisassemblerError(f"初始化反汇编引擎失败: {e}")
        
        self.call_instructions = self.CALL_INSTRUCTIONS.get(architecture, set())
        self.jump_instructions = self.JUMP_INSTRUCTIONS.get(architecture, set())
    
    def disassemble(self, data: bytes, base_address: int = 0) -> Generator[Any, None, None]:
        """
        反汇编字节码
        
        Args:
            data: 要反汇编的字节码
            base_address: 基地址
            
        Yields:
            反汇编指令对象
            
        Raises:
            DisassemblerError: 反汇编失败
        """
        try:
            for instruction in self.cs.disasm(data, base_address):
                yield instruction
        except capstone.CsError as e:
            raise DisassemblerError(f"反汇编失败: {e}")
    
    def disassemble_function(self, data: bytes, base_address: int, size: int) -> List[Dict[str, Any]]:
        """
        反汇编单个函数
        
        Args:
            data: 包含函数的字节码
            base_address: 函数起始地址
            size: 函数大小
            
        Returns:
            指令信息列表
        """
        instructions = []
        function_data = data[:size]
        
        for insn in self.disassemble(function_data, base_address):
            instruction_info = {
                'address': insn.address,
                'mnemonic': insn.mnemonic,
                'op_str': insn.op_str,
                'bytes': insn.bytes,
                'size': insn.size
            }
            
            # 检查是否是调用或跳转指令
            if self.is_call_instruction(insn):
                instruction_info['type'] = 'call'
                target = self.extract_call_target(insn)
                if target:
                    instruction_info['target'] = target
            elif self.is_jump_instruction(insn):
                instruction_info['type'] = 'jump'
                target = self.extract_jump_target(insn)
                if target:
                    instruction_info['target'] = target
            else:
                instruction_info['type'] = 'normal'
            
            instructions.append(instruction_info)
        
        return instructions
    
    def is_call_instruction(self, instruction) -> bool:
        """
        检查指令是否为调用指令
        
        Args:
            instruction: Capstone 指令对象
            
        Returns:
            是否为调用指令
        """
        return instruction.mnemonic in self.call_instructions
    
    def is_jump_instruction(self, instruction) -> bool:
        """
        检查指令是否为跳转指令（可能是尾调用）
        
        Args:
            instruction: Capstone 指令对象
            
        Returns:
            是否为跳转指令
        """
        return instruction.mnemonic in self.jump_instructions
    
    def extract_call_target(self, instruction) -> Optional[int]:
        """
        提取调用指令的目标地址
        
        Args:
            instruction: Capstone 指令对象
            
        Returns:
            目标地址，如果无法确定则返回 None
        """
        return self._extract_target_address(instruction)
    
    def extract_jump_target(self, instruction) -> Optional[int]:
        """
        提取跳转指令的目标地址
        
        Args:
            instruction: Capstone 指令对象
            
        Returns:
            目标地址，如果无法确定则返回 None
        """
        return self._extract_target_address(instruction)
    
    def _extract_target_address(self, instruction) -> Optional[int]:
        """
        从指令中提取目标地址
        
        Args:
            instruction: Capstone 指令对象
            
        Returns:
            目标地址，如果无法确定则返回 None
        """
        # 检查操作数
        if hasattr(instruction, 'operands') and instruction.operands:
            for operand in instruction.operands:
                # 直接地址
                if hasattr(operand, 'type'):
                    if operand.type == capstone.CS_OP_IMM:
                        return operand.imm
                    elif operand.type == capstone.CS_OP_MEM:
                        if hasattr(operand, 'mem') and hasattr(operand.mem, 'disp'):
                            return operand.mem.disp
        
        # 尝试从操作数字符串中解析地址
        if instruction.op_str:
            # 查找十六进制地址
            import re
            hex_match = re.search(r'0x([0-9a-fA-F]+)', instruction.op_str)
            if hex_match:
                try:
                    return int(hex_match.group(1), 16)
                except ValueError:
                    pass
            
            # 查找十进制地址（某些情况下）
            dec_match = re.search(r'\b(\d{4,})\b', instruction.op_str)
            if dec_match:
                try:
                    addr = int(dec_match.group(1))
                    # 合理的地址范围检查
                    if 0x400000 <= addr <= 0x7fffffffffff:
                        return addr
                except ValueError:
                    pass
        
        return None
    
    def find_calls_in_function(self, data: bytes, base_address: int, size: int) -> List[Dict[str, Any]]:
        """
        查找函数中的所有调用
        
        Args:
            data: 包含函数的字节码
            base_address: 函数起始地址
            size: 函数大小
            
        Returns:
            调用信息列表
        """
        calls = []
        instructions = self.disassemble_function(data, base_address, size)
        
        for insn in instructions:
            if insn['type'] in ['call', 'jump']:
                call_info = {
                    'from_address': insn['address'],
                    'instruction': f"{insn['mnemonic']} {insn['op_str']}",
                    'type': insn['type']
                }
                
                if 'target' in insn:
                    call_info['to_address'] = insn['target']
                
                calls.append(call_info)
        
        return calls
    
    def analyze_function_calls(self, function_data: Dict[str, Any], 
                             section_data: bytes, 
                             section_base: int) -> List[Dict[str, Any]]:
        """
        分析函数的调用关系
        
        Args:
            function_data: 函数信息
            section_data: 包含函数的节区数据
            section_base: 节区基地址
            
        Returns:
            调用关系列表
        """
        func_addr = function_data['value']
        func_size = function_data['size']
        
        # 计算函数在节区中的偏移
        offset_in_section = func_addr - section_base
        
        # 确保偏移在有效范围内
        if offset_in_section < 0 or offset_in_section >= len(section_data):
            return []
        
        # 提取函数数据
        end_offset = min(offset_in_section + func_size, len(section_data))
        func_bytes = section_data[offset_in_section:end_offset]
        
        # 查找调用
        calls = self.find_calls_in_function(func_bytes, func_addr, len(func_bytes))
        
        return calls
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'cs'):
            self.cs.close()
