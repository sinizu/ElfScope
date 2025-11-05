# ElfScope MCP 快速启动指南

## 🚀 5分钟快速开始

### 1. 确认安装

```bash
cd /home/heyuhang/efficiency/ElfScope
pip install -e .
```

### 2. 验证安装

```bash
# 检查命令是否可用
elfscope-mcp --help 2>&1 | head -5

# 或者
python -m elfscope.mcp_server --help 2>&1 | head -5
```

### 3. 运行测试

```bash
# 运行所有 MCP 测试
make test-mcp

# 或者
pytest tests/test_mcp_server.py -v
```

预期结果：
```
======================== 27 passed, 1 warning in 1.56s =========================
```

### 4. 启动 MCP 服务器

```bash
# 方式 1: 使用命令
elfscope-mcp

# 方式 2: 使用模块
python -m elfscope.mcp_server

# 方式 3: 使用 Makefile
make mcp-server
```

服务器启动后，会显示：
```
INFO - Starting ElfScope MCP Server...
INFO - Server will communicate via stdio (standard input/output)
INFO - Available tools: elfscope_info, elfscope_analyze, ...
```

### 5. 测试客户端

在另一个终端运行：

```bash
# 使用示例客户端
python examples/mcp_client_example.py /bin/ls

# 或使用 Makefile
make mcp-example
```

## 🔌 Claude Desktop 集成

### 配置步骤

1. 找到 Claude Desktop 配置文件：
   - macOS/Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. 添加 ElfScope MCP 服务器配置：

```json
{
  "mcpServers": {
    "elfscope": {
      "command": "/home/heyuhang/Jarvis/.venv/bin/python",
      "args": ["-m", "elfscope.mcp_server"],
      "env": {
        "PYTHONPATH": "/home/heyuhang/efficiency/ElfScope"
      }
    }
  }
}
```

或者如果 `elfscope-mcp` 在 PATH 中：

```json
{
  "mcpServers": {
    "elfscope": {
      "command": "elfscope-mcp"
    }
  }
}
```

3. 重启 Claude Desktop

4. 在 Claude 中使用：

```
请使用 ElfScope 分析 /bin/ls 文件
```

Claude 将自动调用 MCP 工具进行分析！

## 📋 可用工具列表

| 工具名称 | 功能 |
|---------|------|
| `elfscope_info` | 获取 ELF 文件基本信息 |
| `elfscope_analyze` | 分析函数调用关系 |
| `elfscope_paths` | 查找调用路径 |
| `elfscope_complete` | 完整分析 |
| `elfscope_function` | 分析特定函数 |
| `elfscope_summary` | 生成摘要报告 |
| `elfscope_stack` | 栈使用分析 |
| `elfscope_stack_summary` | 栈使用摘要 |
| `elfscope_objdump` | objdump 功能 |

## 📚 更多文档

- **详细文档**: [MCP_README.md](MCP_README.md)
- **实施报告**: [MCP_IMPLEMENTATION.md](MCP_IMPLEMENTATION.md)
- **主文档**: [README.md](README.md)

## 🐛 故障排除

### 问题 1: 找不到 `elfscope-mcp` 命令

**解决方案**:
```bash
pip uninstall elfscope
pip install -e .
```

### 问题 2: FastMCP 导入错误

**解决方案**:
```bash
pip install fastmcp
```

### 问题 3: 测试失败

**解决方案**:
```bash
# 确保所有依赖已安装
pip install -r requirements.txt
pip install -e .

# 重新运行测试
pytest tests/test_mcp_server.py -v
```

## ✅ 验证清单

完成以下检查确保安装正确：

- [ ] `pip list | grep fastmcp` 显示 fastmcp 已安装
- [ ] `elfscope-mcp --help` 命令可用（或返回服务器信息）
- [ ] `pytest tests/test_mcp_server.py -v` 所有测试通过
- [ ] `python examples/mcp_client_example.py /bin/ls` 可以运行
- [ ] Claude Desktop 配置已添加（如需要）

---

**全部完成！现在 ElfScope 已支持 MCP 协议！** 🎉

