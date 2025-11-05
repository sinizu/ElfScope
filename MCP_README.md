# ElfScope MCP 服务器

ElfScope 现在支持 **Model Context Protocol (MCP)**，可以作为 MCP 服务器运行，让 AI 助手和其他应用程序通过标准化接口访问 ElfScope 的所有功能。

## 🚀 快速开始

### 1. 安装依赖

确保已安装 ElfScope 及其 MCP 依赖：

```bash
# 安装 ElfScope（开发模式）
pip install -e .

# 或者直接安装
pip install .
```

这将自动安装包括 `fastmcp` 在内的所有依赖。

### 2. 启动 MCP 服务器

```bash
# 使用命令行启动
elfscope-mcp

# 或者直接运行模块
python -m elfscope.mcp_server
```

服务器将通过标准输入输出（stdio）进行通信，等待客户端请求。

### 3. 测试 MCP 服务器

使用提供的示例客户端测试服务器功能：

```bash
# 运行示例客户端
python examples/mcp_client_example.py /bin/ls
```

## 📚 可用工具

ElfScope MCP 服务器提供以下工具：

### 1. `elfscope_info`

获取 ELF 文件的基本信息。

**参数：**
- `elf_file` (string): ELF 文件路径

**返回：**
```json
{
  "success": true,
  "data": {
    "architecture": "x86_64",
    "file_type": "ET_EXEC",
    "entry_point": "0x401000",
    "num_sections": 29,
    "num_symbols": 156,
    "num_functions": 42
  },
  "metadata": {...}
}
```

### 2. `elfscope_analyze`

分析 ELF 文件的函数调用关系。

**参数：**
- `elf_file` (string): ELF 文件路径
- `include_stats` (boolean, 可选): 包含统计信息，默认 true
- `include_details` (boolean, 可选): 包含函数详细信息，默认 true

**返回：**
```json
{
  "success": true,
  "data": {
    "metadata": {...},
    "functions": {...},
    "call_relationships": [...],
    "statistics": {
      "total_functions": 42,
      "total_calls": 128,
      "recursive_functions": 3,
      "external_functions": 8
    }
  },
  "metadata": {...}
}
```

### 3. `elfscope_paths`

查找函数间的调用路径。

**参数：**
- `elf_file` (string): ELF 文件路径
- `target_function` (string): 目标函数名称
- `source_function` (string, 可选): 源函数名称
- `max_depth` (integer, 可选): 最大搜索深度，默认 10
- `include_cycles` (boolean, 可选): 包含环，默认 false

**返回：**
```json
{
  "success": true,
  "data": {
    "target_function": "target_func",
    "paths": [
      {
        "path": ["main", "intermediate", "target_func"],
        "length": 2
      }
    ]
  },
  "metadata": {...}
}
```

### 4. `elfscope_complete`

执行完整的 ELF 文件分析。

**参数：**
- `elf_file` (string): ELF 文件路径

**返回：**完整的分析结果，包含文件信息、函数列表、调用关系和统计信息。

### 5. `elfscope_function`

分析特定函数的详细信息。

**参数：**
- `elf_file` (string): ELF 文件路径
- `function_name` (string): 函数名称

**返回：**
```json
{
  "success": true,
  "data": {
    "function_name": "main",
    "callers": [...],
    "callees": [...],
    "is_recursive": false,
    "caller_count": 2,
    "callee_count": 5
  },
  "metadata": {...}
}
```

### 6. `elfscope_summary`

生成 ELF 文件的分析摘要报告。

**参数：**
- `elf_file` (string): ELF 文件路径

**返回：**
```json
{
  "success": true,
  "data": {
    "file_info": {...},
    "statistics": {...},
    "complexity_assessment": "moderate",
    "has_recursion": true,
    "has_cycles": true
  },
  "metadata": {...}
}
```

### 7. `elfscope_stack`

分析指定函数的栈使用情况。

**参数：**
- `elf_file` (string): ELF 文件路径
- `function_name` (string): 函数名称

**返回：**
```json
{
  "success": true,
  "data": {
    "function": "main",
    "local_stack_frame": 112,
    "max_total_stack": 1232,
    "stack_consumed_by_calls": 1120,
    "max_stack_call_path": ["main", "func1", "func2"]
  },
  "metadata": {...}
}
```

### 8. `elfscope_stack_summary`

生成程序的栈使用情况摘要。

**参数：**
- `elf_file` (string): ELF 文件路径
- `top` (integer, 可选): 显示栈消耗最大的函数数量，默认 10

**返回：**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_functions_analyzed": 42,
      "max_total_stack_consumption": 2048
    },
    "heavy_functions": [...]
  },
  "metadata": {...}
}
```

### 9. `elfscope_objdump`

显示 ELF 文件信息（类似 GNU objdump）。

**参数：**
- `elf_file` (string): ELF 文件路径
- `disassemble` (boolean, 可选): 反汇编代码段
- `function` (string, 可选): 反汇编指定函数
- `syms` (boolean, 可选): 显示符号表
- `headers` (boolean, 可选): 显示节区头
- `start_addr` (string, 可选): 起始地址（如 "0x401000"）
- `stop_addr` (string, 可选): 结束地址

**返回：**
```json
{
  "success": true,
  "data": {
    "symbols": {...},
    "headers": {...},
    "disassembly": {...}
  },
  "metadata": {...}
}
```

## 🔌 集成示例

### Claude Desktop 配置

在 Claude Desktop 的配置文件中添加 ElfScope MCP 服务器：

**macOS/Linux**: `~/.config/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "elfscope": {
      "command": "elfscope-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

或者使用 Python 路径：

```json
{
  "mcpServers": {
    "elfscope": {
      "command": "python",
      "args": ["-m", "elfscope.mcp_server"],
      "env": {}
    }
  }
}
```

### Python 客户端示例

```python
from elfscope_mcp_client import ElfScopeMCPClient

# 创建客户端并启动服务器
with ElfScopeMCPClient() as client:
    # 获取文件信息
    result = client.call_tool("elfscope_info", {
        "elf_file": "/bin/ls"
    })
    
    if result["success"]:
        print(f"架构: {result['data']['architecture']}")
    
    # 分析调用关系
    result = client.call_tool("elfscope_analyze", {
        "elf_file": "/bin/ls",
        "include_stats": True
    })
    
    if result["success"]:
        stats = result["data"]["statistics"]
        print(f"函数数: {stats['total_functions']}")
        print(f"调用数: {stats['total_calls']}")
```

### 命令行客户端（使用 jq）

```bash
# 启动服务器
elfscope-mcp &
SERVER_PID=$!

# 发送 JSON-RPC 请求
echo '{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "elfscope_info",
    "arguments": {"elf_file": "/bin/ls"}
  },
  "id": 1
}' | jq -c | nc localhost 3000

# 停止服务器
kill $SERVER_PID
```

## 🛠️ 开发和测试

### 运行测试

```bash
# 运行所有 MCP 测试
pytest tests/test_mcp_server.py -v

# 运行特定测试
pytest tests/test_mcp_server.py::TestElfScopeInfo -v

# 查看测试覆盖率
pytest tests/test_mcp_server.py --cov=elfscope.mcp_server
```

### 调试模式

启用详细日志输出（输出到 stderr，不影响 stdio 通信）：

```bash
# 设置日志级别
export PYTHONUNBUFFERED=1
export ELFSCOPE_LOG_LEVEL=DEBUG
elfscope-mcp
```

### 手动测试

```bash
# 启动服务器（前台运行，可以看到日志）
elfscope-mcp

# 在另一个终端发送测试请求
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"elfscope_info","arguments":{"elf_file":"/bin/ls"}},"id":1}' | elfscope-mcp
```

## 📋 返回格式

所有工具返回统一格式：

**成功响应：**
```json
{
  "success": true,
  "data": { /* 工具特定的数据 */ },
  "metadata": {
    "tool": "elfscope_info",
    "version": "1.0.0",
    "execution_time": 0.123,
    "timestamp": "2025-11-05T12:34:56"
  }
}
```

**错误响应：**
```json
{
  "success": false,
  "error": "文件不存在: /path/to/file",
  "error_type": "FileNotFoundError",
  "metadata": {
    "tool": "elfscope_info",
    "version": "1.0.0",
    "timestamp": "2025-11-05T12:34:56"
  }
}
```

## 🔒 安全注意事项

1. **文件路径验证**：服务器会验证文件路径，防止路径遍历攻击
2. **只读访问**：服务器只读取 ELF 文件，不会修改任何文件
3. **权限检查**：服务器会检查文件读取权限
4. **资源限制**：大文件分析可能需要较长时间，建议设置合理的超时

## 📖 更多资源

- [ElfScope 主文档](README.md)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [示例代码](examples/mcp_client_example.py)

## 🐛 故障排除

### 问题：命令 `elfscope-mcp` 找不到

**解决方案：**
```bash
# 确保已安装 ElfScope
pip install -e .

# 或重新安装
pip uninstall elfscope
pip install -e .
```

### 问题：服务器启动后无响应

**解决方案：**
- 检查 stderr 输出查看错误信息
- 确保 JSON-RPC 请求格式正确
- 验证文件路径是否有效

### 问题：工具调用失败

**解决方案：**
- 检查返回的错误消息和错误类型
- 验证 ELF 文件格式是否正确
- 确保函数名称存在（对于 `elfscope_function` 等工具）

## 📝 更新日志

### v1.0.0 (2025-11-05)
- ✅ 首次发布 MCP 服务器支持
- ✅ 实现所有 9 个 CLI 工具的 MCP 封装
- ✅ 基于 FastMCP 框架
- ✅ 支持 stdio 传输
- ✅ 完整的测试覆盖
- ✅ 提供客户端示例和文档

---

**ElfScope MCP 服务器** - 让 AI 助手能够分析 ELF 文件！🚀

