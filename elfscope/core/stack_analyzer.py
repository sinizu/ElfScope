"""
栈消耗分析模块

该模块分析函数的栈使用情况，包括：
- 分析函数本地栈帧大小
- 计算函数调用链的栈消耗
- 处理递归调用的栈估算
- 估算外部库函数的栈消耗
"""

from typing import Dict, List, Set, Optional, Tuple, Any
import logging
import re
from collections import defaultdict, deque

from .call_analyzer import CallAnalyzer
from .disassembler import Disassembler


class StackAnalysisError(Exception):
    """栈分析相关异常"""
    pass


class StackAnalyzer:
    """
    函数栈消耗分析器
    
    结合反汇编和调用关系分析，计算函数的栈使用情况
    """
    
    # 不同架构的栈指针寄存器和栈操作模式
    ARCH_STACK_INFO = {
        'x86_64': {
            'stack_pointer': ['rsp', 'esp'],
            'frame_pointer': ['rbp', 'ebp'],
            'stack_alloc_patterns': [
                r'sub\s+(?:rsp|esp),\s*(?:0x)?([0-9a-fA-F]+)',  # sub rsp, 0x20
                r'lea\s+(?:rsp|esp),\s*\[(?:rsp|esp)\s*-\s*(?:0x)?([0-9a-fA-F]+)\]'  # lea rsp, [rsp-0x20]
            ],
            'push_size': 8,  # 64位架构推入8字节
            'alignment': 16  # 栈对齐要求
        },
        'x86': {
            'stack_pointer': ['esp'],
            'frame_pointer': ['ebp'],
            'stack_alloc_patterns': [
                r'sub\s+esp,\s*(?:0x)?([0-9a-fA-F]+)',
                r'lea\s+esp,\s*\[esp\s*-\s*(?:0x)?([0-9a-fA-F]+)\]'
            ],
            'push_size': 4,
            'alignment': 4
        },
        'aarch64': {
            'stack_pointer': ['sp', 'x31'],
            'frame_pointer': ['x29', 'fp'],
            'stack_alloc_patterns': [
                r'sub\s+sp,\s*sp,\s*#(?:0x)?([0-9a-fA-F]+)',  # sub sp, sp, #0x20
                r'add\s+sp,\s*sp,\s*#-(?:0x)?([0-9a-fA-F]+)'  # add sp, sp, #-0x20
            ],
            'push_size': 8,
            'alignment': 16
        },
        'arm': {
            'stack_pointer': ['sp', 'r13'],
            'frame_pointer': ['fp', 'r11'],
            'stack_alloc_patterns': [
                r'sub\s+sp,\s*(?:sp,\s*)?#(?:0x)?([0-9a-fA-F]+)',
                r'sub\s+r13,\s*(?:r13,\s*)?#(?:0x)?([0-9a-fA-F]+)'
            ],
            'push_size': 4,
            'alignment': 8
        }
    }
    
    # 外部库函数的预估栈消耗（字节）
    EXTERNAL_FUNC_STACK_ESTIMATES = {
        # C 标准库函数
        'printf': 64, 'fprintf': 64, 'sprintf': 48, 'snprintf': 48,
        'scanf': 32, 'fscanf': 32, 'sscanf': 32,
        'malloc': 32, 'free': 16, 'realloc': 32, 'calloc': 32,
        'memcpy': 16, 'memset': 16, 'memcmp': 16, 'memmove': 16,
        'strcpy': 24, 'strncpy': 24, 'strcmp': 24, 'strncmp': 24,
        'strlen': 16, 'strcat': 24, 'strncat': 24,
        'fopen': 64, 'fclose': 32, 'fread': 48, 'fwrite': 48,
        'fseek': 32, 'ftell': 16, 'rewind': 16,
        'exit': 32, 'abort': 32, 'atexit': 24,
        # 数学库函数
        'sin': 32, 'cos': 32, 'tan': 32, 'sqrt': 32, 'pow': 48, 'exp': 32, 'log': 32,
        # 系统调用相关
        'open': 32, 'close': 16, 'read': 32, 'write': 32, 'lseek': 32,
        'getpid': 16, 'fork': 48, 'exec': 64, 'wait': 32,
        # 线程相关
        'pthread_create': 128, 'pthread_join': 64, 'pthread_mutex_lock': 32,
        'pthread_mutex_unlock': 16, 'pthread_cond_wait': 64,
    }
    
    def __init__(self, call_analyzer: CallAnalyzer):
        """
        初始化栈分析器
        
        Args:
            call_analyzer: 函数调用关系分析器
        """
        self.call_analyzer = call_analyzer
        self.architecture = call_analyzer.architecture
        
        if self.architecture not in self.ARCH_STACK_INFO:
            logging.warning(f"架构 {self.architecture} 的栈分析支持有限")
            # 使用默认的x86_64配置
            self.arch_info = self.ARCH_STACK_INFO['x86_64']
        else:
            self.arch_info = self.ARCH_STACK_INFO[self.architecture]
        
        # 栈分析数据
        self.function_stack_frames = {}  # 函数名 -> 栈帧大小
        self.function_max_stack = {}     # 函数名 -> 最大栈消耗（包含调用链）
        self.function_max_stack_paths = {}  # 函数名 -> 最大栈消耗时的调用路径
        self.analyzed = False
        
    def analyze(self) -> None:
        """执行栈分析"""
        logging.info(f"开始分析 {self.call_analyzer.elf_parser.filepath} 的栈使用情况")
        
        # 确保调用关系已分析
        if not self.call_analyzer.analyzed:
            self.call_analyzer.analyze()
        
        # 分析每个函数的栈帧大小
        self._analyze_stack_frames()
        
        # 计算调用链栈消耗
        self._calculate_call_chain_stack()
        
        self.analyzed = True
        logging.info("栈分析完成")
        
    def _analyze_stack_frames(self) -> None:
        """分析每个函数的本地栈帧大小"""
        functions = self.call_analyzer.elf_parser.get_functions()
        code_sections = self.call_analyzer.elf_parser.get_text_sections()
        
        for function in functions:
            func_name = function['name']
            func_addr = function['value']
            func_size = function.get('size', 0)
            
            if func_size == 0:
                self.function_stack_frames[func_name] = 0
                continue
            
            # 找到包含此函数的代码段
            section_data = None
            section_base = 0
            
            for section in code_sections:
                section_start = section['addr']
                section_end = section_start + section['size']
                
                if section_start <= func_addr < section_end:
                    # 从ELF文件中读取段数据
                    section_data = self.call_analyzer.elf_parser.get_section_data(section['name'])
                    section_base = section_start
                    break
            
            if section_data is None:
                self.function_stack_frames[func_name] = 0
                continue
            
            # 分析函数的栈帧
            try:
                stack_frame_size = self._analyze_function_stack_frame(
                    function, section_data, section_base
                )
                self.function_stack_frames[func_name] = stack_frame_size
            except Exception as e:
                logging.warning(f"分析函数 {func_name} 栈帧时出错: {e}")
                self.function_stack_frames[func_name] = 0
    
    def _analyze_function_stack_frame(self, 
                                     function: Dict[str, Any], 
                                     section_data: bytes, 
                                     section_base: int) -> int:
        """
        分析单个函数的栈帧大小
        
        Args:
            function: 函数信息
            section_data: 代码段数据
            section_base: 代码段基地址
            
        Returns:
            栈帧大小（字节）
        """
        func_name = function['name']
        func_addr = function['value']
        func_size = function.get('size', 0)
        
        if func_size == 0:
            return 0
        
        # 计算在段内的偏移
        offset = func_addr - section_base
        if offset < 0 or offset >= len(section_data):
            return 0
        
        # 获取函数的机器码
        func_data = section_data[offset:offset + func_size]
        
        # 反汇编函数
        disassembler = self.call_analyzer.disassembler
        instructions = disassembler.disassemble_function(func_data, func_addr, func_size)
        
        # 分析栈操作指令
        stack_size = 0
        push_count = 0
        
        # 只分析函数开头的几条指令（函数序言）
        prologue_instructions = instructions[:min(20, len(instructions))]
        
        for insn in prologue_instructions:
            mnemonic = insn['mnemonic'].lower()
            op_str = insn['op_str'].lower()
            
            # 检查栈分配指令
            for pattern in self.arch_info['stack_alloc_patterns']:
                match = re.search(pattern, f"{mnemonic} {op_str}", re.IGNORECASE)
                if match:
                    try:
                        # 提取分配的字节数
                        alloc_size = int(match.group(1), 16 if 'x' in match.group(1).lower() else 10)
                        stack_size = max(stack_size, alloc_size)
                    except (ValueError, IndexError):
                        continue
            
            # 统计push指令
            if mnemonic == 'push':
                push_count += 1
        
        # 加上push指令的栈消耗
        push_stack = push_count * self.arch_info['push_size']
        total_stack = stack_size + push_stack
        
        # 应用栈对齐
        alignment = self.arch_info['alignment']
        if total_stack % alignment != 0:
            total_stack = ((total_stack // alignment) + 1) * alignment
        
        return total_stack
    
    def _calculate_call_chain_stack(self) -> None:
        """计算函数调用链的总栈消耗并记录调用路径"""
        call_graph = self.call_analyzer.call_graph
        
        # 使用DFS计算每个函数的最大栈消耗和对应路径
        visited = set()
        calculating = set()  # 正在计算的函数（用于检测递归）
        
        def calculate_max_stack_with_path(func_name: str, current_path: List[str] = None) -> Tuple[int, List[str]]:
            if current_path is None:
                current_path = []
            
            # 检测循环调用：如果当前函数已经在路径中，说明形成了循环
            if func_name in current_path:
                # 找到循环的起点
                cycle_start_idx = current_path.index(func_name)
                cycle_path = current_path[cycle_start_idx:] + [func_name]
                
                # 计算循环中所有函数的栈消耗总和
                cycle_stack = 0
                for func in cycle_path[:-1]:  # 不包括最后一个重复的函数
                    func_stack = self.function_stack_frames.get(func, 0)
                    if func not in self.function_stack_frames:
                        func_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(func, 32)
                    cycle_stack += func_stack
                
                # 估算递归深度为10层
                recursive_stack = cycle_stack * 10
                
                # 构建循环标记：只返回循环标记，不包含路径前缀
                # 因为 func_name 已经在 current_path 中，上层函数会正确拼接
                cycle_funcs = ' → '.join(cycle_path[:-1])
                recursive_path = [f"[循环: {cycle_funcs}] (递归 x10)"]
                
                return recursive_stack, recursive_path
            
            # 检测直接递归（函数调用自己）
            if func_name in calculating:
                # 检测到递归调用，返回一个估算值
                base_stack = self.function_stack_frames.get(func_name, 0)
                if func_name not in self.function_stack_frames:
                    base_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(func_name, 32)
                recursive_stack = base_stack * 10  # 递归深度估算为10层
                # 只返回递归标记，不包含 current_path
                recursive_path = [f"{func_name} (递归 x10)"]
                return recursive_stack, recursive_path
            
            if func_name in visited:
                # 如果函数已经计算过，检查是否会形成循环
                if func_name in current_path:
                    # 如果在当前路径中已经存在，说明形成了循环
                    # 找到循环的起点
                    cycle_start_idx = current_path.index(func_name)
                    cycle_path = current_path[cycle_start_idx:] + [func_name]
                    
                    # 计算循环中所有函数的栈消耗总和
                    cycle_stack = 0
                    for func in cycle_path[:-1]:
                        func_stack = self.function_stack_frames.get(func, 0)
                        if func not in self.function_stack_frames:
                            func_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(func, 32)
                        cycle_stack += func_stack
                    
                    recursive_stack = cycle_stack * 10
                    cycle_funcs = ' → '.join(cycle_path[:-1])
                    recursive_path = [f"[循环: {cycle_funcs}] (递归 x10)"]
                    return recursive_stack, recursive_path
                
                # 如果不会形成循环，返回缓存的结果
                # 注意：缓存路径包含完整路径，但我们需要返回从函数开始的路径
                cached_full_path = self.function_max_stack_paths.get(func_name, [])
                if cached_full_path:
                    # 从缓存路径中提取从函数开始的路径
                    # 找到函数在路径中的位置
                    if func_name in cached_full_path:
                        func_idx = cached_full_path.index(func_name)
                        cached_path = cached_full_path[func_idx:]
                    else:
                        cached_path = [func_name]
                else:
                    cached_path = [func_name]
                return self.function_max_stack.get(func_name, 0), cached_path
            
            calculating.add(func_name)
            
            # 本函数的栈帧大小
            local_stack = self.function_stack_frames.get(func_name, 0)
            
            # 如果是外部函数，使用预估值
            if func_name not in self.function_stack_frames:
                local_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(func_name, 32)
            
            max_callee_stack = 0
            max_callee_path = []
            
            # 检查所有被调用的函数
            if func_name in call_graph:
                for callee in call_graph.successors(func_name):
                    # 构建新的路径，包含当前函数
                    new_path = current_path + [func_name]
                    
                    callee_stack, callee_path = calculate_max_stack_with_path(
                        callee, new_path
                    )
                    
                    if callee_stack > max_callee_stack:
                        max_callee_stack = callee_stack
                        max_callee_path = callee_path
            
            total_stack = local_stack + max_callee_stack
            
            # 构建从当前函数开始的调用路径（不包含 current_path）
            # max_callee_path 是从被调用函数开始的路径（不包含 current_path）
            # 例如：如果 puts 调用 __free，__free 返回的路径是 ['__free', '_int_free', ...]
            # 那么 puts 返回的路径应该是 ['puts'] + ['__free', '_int_free', ...]
            # 注意：返回的路径只包含从当前函数开始的调用链，调用者会自己拼接完整路径
            if max_callee_path:
                # 检查 max_callee_path 是否以循环标记开始
                if max_callee_path and max_callee_path[0].startswith("[循环:"):
                    # 如果被调用函数检测到循环，说明 func_name 已经在 current_path 中
                    # 此时只返回循环标记，不包含 func_name
                    return_path = max_callee_path
                else:
                    # max_callee_path 已经包含被调用函数，直接拼接即可
                    # 返回的路径从当前函数开始：['func_name'] + max_callee_path
                    return_path = [func_name] + max_callee_path
            else:
                # 如果没有调用其他函数，只返回当前函数
                return_path = [func_name]
            
            # 保存完整路径（用于缓存，包含 current_path）
            full_path = current_path + return_path
            self.function_max_stack[func_name] = total_stack
            self.function_max_stack_paths[func_name] = full_path
            calculating.remove(func_name)
            visited.add(func_name)
            
            # 返回从当前函数开始的路径（不包含 current_path）
            return total_stack, return_path
        
        # 计算所有函数的栈消耗和路径
        for func_name in call_graph.nodes():
            if func_name not in visited:
                calculate_max_stack_with_path(func_name)
    
    def get_function_stack_info(self, function_name: str) -> Dict[str, Any]:
        """
        获取单个函数的栈信息
        
        Args:
            function_name: 函数名
            
        Returns:
            函数的栈信息
        """
        if not self.analyzed:
            self.analyze()
        
        if function_name not in self.call_analyzer.call_graph:
            return {
                'function': function_name,
                'error': f"函数 '{function_name}' 不存在",
                'found': False
            }
        
        local_stack = self.function_stack_frames.get(function_name, 0)
        max_stack = self.function_max_stack.get(function_name, 0)
        max_stack_path = self.function_max_stack_paths.get(function_name, [])
        
        # 获取调用的函数
        callees = list(self.call_analyzer.call_graph.successors(function_name))
        callee_info = []
        
        for callee in callees:
            callee_stack = self.function_stack_frames.get(callee, 0)
            is_external = callee not in self.function_stack_frames
            if is_external:
                callee_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(callee, 32)
            
            callee_info.append({
                'function': callee,
                'stack_frame': callee_stack,
                'external': is_external
            })
        
        # 构建路径详情（包含每个函数的栈消耗）
        path_details = []
        current_total = 0
        
        for i, func in enumerate(max_stack_path):
            if func.endswith("(递归 x10)"):
                # 处理递归或循环调用
                if func.startswith("[循环:"):
                    # 处理循环调用标记：提取循环中的函数列表
                    # 格式: [循环: func1 → func2 → ...] (递归 x10)
                    cycle_match = func.split("[循环:")[1].split("]")[0]
                    cycle_funcs = [f.strip() for f in cycle_match.split("→")]
                    
                    # 计算循环中所有函数的栈消耗总和
                    cycle_stack = 0
                    for cycle_func in cycle_funcs:
                        func_stack = self.function_stack_frames.get(cycle_func, 0)
                        if cycle_func not in self.function_stack_frames:
                            func_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(cycle_func, 32)
                        cycle_stack += func_stack
                    
                    recursive_stack = cycle_stack * 10
                    current_total += recursive_stack
                    path_details.append({
                        'function': func,
                        'local_stack': recursive_stack,
                        'cumulative_stack': current_total,
                        'is_recursive': True,
                        'is_cycle': True,
                        'cycle_functions': cycle_funcs
                    })
                else:
                    # 处理直接递归函数
                    base_func = func.replace(" (递归 x10)", "")
                    func_local_stack = self.function_stack_frames.get(base_func, 0)
                    if base_func not in self.function_stack_frames:
                        func_local_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(base_func, 32)
                    recursive_stack = func_local_stack * 10
                    current_total += recursive_stack
                    path_details.append({
                        'function': func,
                        'local_stack': recursive_stack,
                        'cumulative_stack': current_total,
                        'is_recursive': True,
                        'is_cycle': False
                    })
            else:
                func_local_stack = self.function_stack_frames.get(func, 0)
                if func not in self.function_stack_frames:
                    func_local_stack = self.EXTERNAL_FUNC_STACK_ESTIMATES.get(func, 32)
                
                current_total += func_local_stack
                path_details.append({
                    'function': func,
                    'local_stack': func_local_stack,
                    'cumulative_stack': current_total,
                    'is_external': func not in self.function_stack_frames,
                    'is_recursive': False
                })
        
        return {
            'function': function_name,
            'local_stack_frame': local_stack,
            'max_total_stack': max_stack,
            'stack_consumed_by_calls': max_stack - local_stack,
            'max_stack_call_path': max_stack_path,
            'max_stack_path_details': path_details,
            'called_functions': callee_info,
            'architecture': self.architecture,
            'found': True
        }
    
    def get_stack_summary(self) -> Dict[str, Any]:
        """
        获取栈使用情况摘要
        
        Returns:
            栈使用摘要信息
        """
        if not self.analyzed:
            self.analyze()
        
        # 统计信息
        total_functions = len(self.function_stack_frames)
        functions_with_stack = sum(1 for size in self.function_stack_frames.values() if size > 0)
        
        # 找出栈消耗最大的函数
        max_local_stack = max(self.function_stack_frames.values()) if self.function_stack_frames else 0
        max_total_stack = max(self.function_max_stack.values()) if self.function_max_stack else 0
        
        max_local_func = None
        max_total_func = None
        max_total_func_path = []
        
        for func, size in self.function_stack_frames.items():
            if size == max_local_stack:
                max_local_func = func
                break
        
        for func, size in self.function_max_stack.items():
            if size == max_total_stack:
                max_total_func = func
                max_total_func_path = self.function_max_stack_paths.get(func, [])
                break
        
        # 栈使用分布
        stack_distribution = {
            'small': 0,      # < 64 bytes
            'medium': 0,     # 64-256 bytes
            'large': 0,      # 256-1024 bytes
            'huge': 0        # > 1024 bytes
        }
        
        for size in self.function_max_stack.values():
            if size < 64:
                stack_distribution['small'] += 1
            elif size < 256:
                stack_distribution['medium'] += 1
            elif size < 1024:
                stack_distribution['large'] += 1
            else:
                stack_distribution['huge'] += 1
        
        return {
            'architecture': self.architecture,
            'total_functions_analyzed': total_functions,
            'functions_with_stack': functions_with_stack,
            'max_local_stack_frame': max_local_stack,
            'max_total_stack_consumption': max_total_stack,
            'function_with_max_local_stack': max_local_func,
            'function_with_max_total_stack': max_total_func,
            'max_total_stack_call_path': max_total_func_path,
            'stack_distribution': stack_distribution,
            'stack_pointer_register': self.arch_info['stack_pointer'][0],
            'stack_alignment': self.arch_info['alignment']
        }
    
    def find_stack_heavy_functions(self, limit: int = 10, 
                                  sort_by: str = 'total') -> List[Dict[str, Any]]:
        """
        找出栈消耗最大的函数
        
        Args:
            limit: 返回的函数数量限制
            sort_by: 排序方式，'total'(总栈消耗) 或 'local'(本地栈帧)
            
        Returns:
            栈消耗最大的函数列表
        """
        if not self.analyzed:
            self.analyze()
        
        functions = []
        
        for func_name in self.function_stack_frames:
            local_stack = self.function_stack_frames.get(func_name, 0)
            total_stack = self.function_max_stack.get(func_name, 0)
            call_path = self.function_max_stack_paths.get(func_name, [])
            
            functions.append({
                'function': func_name,
                'local_stack_frame': local_stack,
                'max_total_stack': total_stack,
                'max_stack_call_path': call_path,
                'stack_ratio': total_stack / local_stack if local_stack > 0 else 0
            })
        
        # 排序
        if sort_by == 'local':
            functions.sort(key=lambda x: x['local_stack_frame'], reverse=True)
        else:  # total
            functions.sort(key=lambda x: x['max_total_stack'], reverse=True)
        
        return functions[:limit]
