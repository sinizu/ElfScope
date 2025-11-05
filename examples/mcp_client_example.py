#!/usr/bin/env python3
"""
ElfScope MCP 客户端示例

演示如何通过标准输入输出（stdio）与 ElfScope MCP 服务器通信。

这个示例展示了：
1. 如何启动 MCP 服务器进程
2. 如何发送 JSON-RPC 请求
3. 如何接收和解析响应
4. 如何调用不同的工具

注意：这是一个简化的示例。实际使用中，建议使用专门的 MCP 客户端库。
"""

import json
import subprocess
import sys
from typing import Dict, Any, Optional


class ElfScopeMCPClient:
    """
    ElfScope MCP 客户端
    
    通过 stdio 与 ElfScope MCP 服务器通信
    """
    
    def __init__(self, server_command: str = "elfscope-mcp"):
        """
        初始化 MCP 客户端
        
        Args:
            server_command: MCP 服务器启动命令
        """
        self.server_command = server_command
        self.process = None
        self.request_id = 0
    
    def start(self):
        """启动 MCP 服务器进程"""
        try:
            self.process = subprocess.Popen(
                [self.server_command],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            print(f"✓ MCP 服务器已启动 (PID: {self.process.pid})")
        except FileNotFoundError:
            print(f"✗ 错误: 找不到命令 '{self.server_command}'")
            print("   请确保已安装 ElfScope 并运行: pip install -e .")
            sys.exit(1)
    
    def stop(self):
        """停止 MCP 服务器进程"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            print("✓ MCP 服务器已停止")
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具返回的结果
        """
        if not self.process:
            raise RuntimeError("MCP 服务器未启动")
        
        # 构造 JSON-RPC 请求
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": self.request_id
        }
        
        # 发送请求
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
        # 接收响应
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP 服务器无响应")
        
        response = json.loads(response_line)
        
        # 检查错误
        if "error" in response:
            raise RuntimeError(f"MCP 错误: {response['error']}")
        
        return response.get("result", {})
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


# ============================================================================
# 使用示例
# ============================================================================

def example_info(client: ElfScopeMCPClient, elf_file: str):
    """示例：获取 ELF 文件信息"""
    print("\n" + "="*60)
    print("示例 1: 获取 ELF 文件基本信息")
    print("="*60)
    
    result = client.call_tool("elfscope_info", {"elf_file": elf_file})
    
    if result.get("success"):
        data = result["data"]
        print(f"✓ 文件: {elf_file}")
        print(f"  架构: {data['architecture']}")
        print(f"  文件类型: {data['file_type']}")
        print(f"  入口点: {data['entry_point']}")
        print(f"  函数数量: {data['num_functions']}")
    else:
        print(f"✗ 错误: {result.get('error')}")


def example_analyze(client: ElfScopeMCPClient, elf_file: str):
    """示例：分析函数调用关系"""
    print("\n" + "="*60)
    print("示例 2: 分析函数调用关系")
    print("="*60)
    
    result = client.call_tool("elfscope_analyze", {
        "elf_file": elf_file,
        "include_stats": True,
        "include_details": False
    })
    
    if result.get("success"):
        data = result["data"]
        stats = data.get("statistics", {})
        print(f"✓ 分析完成")
        print(f"  总函数数: {stats.get('total_functions', 0)}")
        print(f"  调用关系: {stats.get('total_calls', 0)}")
        print(f"  递归函数: {stats.get('recursive_functions', 0)}")
        print(f"  外部函数: {stats.get('external_functions', 0)}")
        print(f"  执行时间: {result['metadata']['execution_time']}秒")
    else:
        print(f"✗ 错误: {result.get('error')}")


def example_summary(client: ElfScopeMCPClient, elf_file: str):
    """示例：生成摘要报告"""
    print("\n" + "="*60)
    print("示例 3: 生成摘要报告")
    print("="*60)
    
    result = client.call_tool("elfscope_summary", {"elf_file": elf_file})
    
    if result.get("success"):
        data = result["data"]
        print(f"✓ 摘要报告")
        print(f"  复杂度: {data['complexity_assessment']}")
        print(f"  有递归: {data['has_recursion']}")
        print(f"  有环: {data['has_cycles']}")
    else:
        print(f"✗ 错误: {result.get('error')}")


def example_paths(client: ElfScopeMCPClient, elf_file: str):
    """示例：查找调用路径"""
    print("\n" + "="*60)
    print("示例 4: 查找函数调用路径")
    print("="*60)
    
    result = client.call_tool("elfscope_paths", {
        "elf_file": elf_file,
        "target_function": "main",
        "max_depth": 10
    })
    
    if result.get("success"):
        data = result["data"]
        paths = data.get("paths", [])
        print(f"✓ 找到 {len(paths)} 条调用路径")
        
        # 显示前3条路径
        for i, path_info in enumerate(paths[:3], 1):
            path = path_info.get("path", [])
            print(f"  路径 {i}: {' → '.join(path)}")
    else:
        print(f"✗ 错误: {result.get('error')}")


def example_stack(client: ElfScopeMCPClient, elf_file: str):
    """示例：栈使用分析"""
    print("\n" + "="*60)
    print("示例 5: 栈使用分析")
    print("="*60)
    
    result = client.call_tool("elfscope_stack", {
        "elf_file": elf_file,
        "function_name": "main"
    })
    
    if result.get("success"):
        data = result["data"]
        print(f"✓ 栈分析: {data.get('function', 'main')}")
        print(f"  本地栈帧: {data.get('local_stack_frame', 0)} 字节")
        print(f"  最大总栈: {data.get('max_total_stack', 0)} 字节")
        print(f"  调用栈消耗: {data.get('stack_consumed_by_calls', 0)} 字节")
    else:
        print(f"✗ 错误: {result.get('error')}")


def example_objdump(client: ElfScopeMCPClient, elf_file: str):
    """示例：显示符号表"""
    print("\n" + "="*60)
    print("示例 6: 显示符号表（前10个）")
    print("="*60)
    
    result = client.call_tool("elfscope_objdump", {
        "elf_file": elf_file,
        "syms": True
    })
    
    if result.get("success"):
        data = result["data"]
        symbols = data.get("symbols", {}).get("symbols", [])
        print(f"✓ 符号总数: {len(symbols)}")
        
        # 显示前10个符号
        for sym in symbols[:10]:
            print(f"  {sym['name']}: {sym['value']} ({sym['type']})")
    else:
        print(f"✗ 错误: {result.get('error')}")


def main():
    """主函数"""
    print("="*60)
    print("ElfScope MCP 客户端示例")
    print("="*60)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python mcp_client_example.py <elf_file>")
        print("\n示例:")
        print("  python mcp_client_example.py /bin/ls")
        sys.exit(1)
    
    elf_file = sys.argv[1]
    
    # 使用上下文管理器自动管理服务器生命周期
    try:
        with ElfScopeMCPClient() as client:
            # 运行所有示例
            example_info(client, elf_file)
            example_analyze(client, elf_file)
            example_summary(client, elf_file)
            example_paths(client, elf_file)
            example_stack(client, elf_file)
            example_objdump(client, elf_file)
            
            print("\n" + "="*60)
            print("✓ 所有示例执行完成")
            print("="*60)
    
    except KeyboardInterrupt:
        print("\n✗ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

