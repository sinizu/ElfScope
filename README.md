# ElfScope

**ElfScope** 是一个强大的 ELF 文件函数调用关系分析工具，支持多种架构的反汇编和调用路径查找。

## 功能特性

### 🔍 核心功能
- **多架构支持**: 支持 x86_64、x86、ARM、AArch64、MIPS、PowerPC、RISC-V 等主流架构
- **函数调用关系分析**: 自动识别和分析 ELF 文件中的函数调用关系
- **调用路径查找**: 查找从父函数到子函数的所有可能调用路径
- **JSON 格式导出**: 将分析结果导出为结构化的 JSON 文件

### 🛠️ 技术特点
- **Clean Code**: 代码结构清晰，模块化设计，易于维护和扩展
- **高性能**: 使用 Capstone 反汇编引擎和 NetworkX 图算法库，性能优异
- **全面测试**: 完整的单元测试和集成测试覆盖
- **命令行友好**: 提供直观的命令行接口，支持多种分析模式

## 安装

### 环境要求
- Python 3.8 或更高版本
- Linux 操作系统（推荐）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 开发安装
```bash
pip install -e .
```

## 🎯 快速体验

### 🚀 一键演示（推荐）

想要快速体验 ElfScope 的所有功能？我们提供了完整的演示环境：

```bash
# 进入演示目录
cd demo

# 运行自动化演示（推荐）
python3 run_demo.py

# 或者运行快速启动脚本
./quick_start.sh
```

演示包含：
- 📊 **复杂测试程序** - 600行C代码，包含各种调用模式
- 🔍 **完整功能展示** - 所有核心功能的自动化演示  
- 📁 **结果文件** - 生成详细的JSON分析报告
- 📖 **详细说明** - 完整的使用指南和示例

**5分钟内完全掌握 ElfScope！** 🎉

## 快速开始

### 1. 分析 ELF 文件的函数调用关系

```bash
# 分析二进制文件的所有函数调用关系
elfscope analyze /path/to/binary -o analysis.json

# 包含统计信息和详细信息
elfscope analyze ./program -o results.json --include-stats --include-details
```

### 2. 查找函数调用路径

```bash
# 查找所有到 target_function 的调用路径
elfscope paths /path/to/binary target_function -o paths.json

# 查找从 source_function 到 target_function 的路径
elfscope paths /path/to/binary target_function -s source_function -o paths.json

# 限制搜索深度并包含循环调用
elfscope paths /path/to/binary target_function -d 5 --include-cycles -o paths.json
```

### 3. 完整分析

```bash
# 执行完整的 ELF 文件分析
elfscope complete /path/to/binary -o complete_analysis.json
```

### 4. 查看 ELF 文件信息

```bash
# 显示 ELF 文件基本信息
elfscope info /path/to/binary
```

## Python API 使用

```python
from elfscope import ElfParser, CallAnalyzer, PathFinder, JsonExporter

# 1. 解析 ELF 文件
parser = ElfParser('/path/to/binary')
print(f"架构: {parser.get_architecture()}")
print(f"函数数量: {len(parser.get_functions())}")

# 2. 分析调用关系
analyzer = CallAnalyzer(parser)
analyzer.analyze()

# 获取调用关系
relationships = analyzer.get_call_relationships()
print(f"调用关系数量: {len(relationships['calls'])}")

# 3. 查找调用路径
path_finder = PathFinder(analyzer)
paths = path_finder.find_paths(
    target_function='target_func',
    source_function='source_func'
)

# 4. 导出结果
exporter = JsonExporter()
exporter.export_call_relationships(
    call_analyzer=analyzer,
    output_file='analysis.json'
)
```

## 输出格式

### 调用关系分析输出

```json
{
  "metadata": {
    "tool_name": "ElfScope",
    "version": "1.0.0",
    "export_time": "2024-01-01T00:00:00",
    "elf_file": "/path/to/binary",
    "architecture": "x86_64"
  },
  "functions": {
    "main": {
      "name": "main",
      "address": "0x401000",
      "size": 100,
      "type": "STT_FUNC",
      "external": false
    }
  },
  "call_relationships": [
    {
      "from_function": "main",
      "to_function": "helper_func",
      "from_address": "0x401010",
      "to_address": "0x401100",
      "instruction": "call 0x401100",
      "type": "call"
    }
  ],
  "statistics": {
    "total_functions": 10,
    "total_calls": 25,
    "external_functions": 3,
    "recursive_functions": 1,
    "average_calls_per_function": 2.5
  }
}
```

### 调用路径分析输出

```json
{
  "metadata": {
    "tool_name": "ElfScope",
    "query": {
      "target_function": "target_func",
      "source_function": "source_func",
      "max_depth": 10
    }
  },
  "path_analysis": {
    "target_function": "target_func",
    "source_function": "source_func",
    "paths": [
      {
        "path": ["source_func", "intermediate_func", "target_func"],
        "length": 2,
        "steps": [
          {
            "step": 1,
            "from": "source_func",
            "to": "intermediate_func",
            "calls": [...]
          }
        ]
      }
    ],
    "statistics": {
      "total_paths": 3,
      "max_depth": 3,
      "min_depth": 2,
      "average_depth": 2.3
    }
  }
}
```

## 架构支持

| 架构 | 支持状态 | 说明 |
|------|----------|------|
| x86_64 | ✅ 完全支持 | Intel/AMD 64位架构 |
| x86 | ✅ 完全支持 | Intel/AMD 32位架构 |
| ARM | ✅ 完全支持 | ARM 32位架构 |
| AArch64 | ✅ 完全支持 | ARM 64位架构 |
| MIPS | ✅ 完全支持 | MIPS 架构 |
| PowerPC | ✅ 完全支持 | PowerPC 32/64位 |
| RISC-V | ✅ 完全支持 | RISC-V 架构 |

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 生成覆盖率报告
pytest --cov=elfscope --cov-report=html
```

### 代码风格

项目遵循 PEP 8 代码风格规范，使用以下工具进行代码质量管理：

```bash
# 代码格式化
black elfscope/

# 代码检查
flake8 elfscope/

# 类型检查
mypy elfscope/
```

## 项目结构

```
ElfScope/
├── elfscope/                 # 主要源代码
│   ├── core/                # 核心模块
│   │   ├── elf_parser.py    # ELF文件解析
│   │   ├── disassembler.py  # 反汇编引擎
│   │   ├── call_analyzer.py # 调用关系分析
│   │   └── path_finder.py   # 路径查找
│   ├── utils/               # 工具模块
│   │   └── json_exporter.py # JSON导出
│   └── cli.py               # 命令行接口
├── tests/                   # 测试用例
├── requirements.txt         # 依赖列表
├── setup.py                # 安装脚本
├── pytest.ini             # pytest配置
└── README.md               # 项目文档
```

## 性能特点

- **内存高效**: 使用流式处理，支持分析大型 ELF 文件
- **速度优化**: 多级缓存和优化的图算法，分析速度快
- **可扩展**: 模块化架构，易于添加新功能和支持新架构

## 应用场景

- **逆向工程**: 分析二进制文件的内部结构和调用关系
- **安全研究**: 识别潜在的安全漏洞和攻击路径
- **代码审计**: 理解复杂系统的函数调用流程
- **性能分析**: 识别热点函数和调用瓶颈
- **依赖分析**: 分析模块间的依赖关系

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 联系方式

- GitHub Issues: [https://github.com/elfscope/elfscope/issues](https://github.com/elfscope/elfscope/issues)
- 邮箱: elfscope@example.com

## 更新日志

### v1.0.0 (2024-01-01)
- 🎉 首个稳定版本发布
- ✅ 支持多架构 ELF 文件分析
- ✅ 完整的函数调用关系分析
- ✅ 调用路径查找功能
- ✅ JSON 格式导出
- ✅ 命令行工具
- ✅ 完整的测试覆盖

---

**ElfScope** - 让 ELF 文件分析变得简单高效！
