# ElfScope 演示指南

欢迎使用 **ElfScope** - 专业的ELF文件函数调用关系分析工具！

这个演示文件夹包含了完整的示例程序和自动化演示脚本，帮助你快速了解和体验 ElfScope 的所有功能。

## 📁 文件说明

### 核心演示文件
- **`test_program.c`** - 复杂的C测试程序（600行代码）
  - 包含递归、相互递归、深度调用链、函数指针等复杂调用模式
  - 专门设计用于测试ElfScope的各种分析能力
- **`test_program`** - 编译后的ELF二进制文件（x86_64架构）
- **`run_demo.py`** - 自动化演示脚本 ⭐
- **`README.md`** - 本说明文档

### 分析结果文件
演示过程会生成以下分析结果文件（保存在 `output/` 目录中）：
- **`output/demo_analysis.json`** - 完整的函数调用关系分析
- **`output/demo_fibonacci_paths.json`** - 从main到fibonacci_recursive的调用路径
- **`output/demo_utility_paths.json`** - 所有调用utility_function_1的路径
- **`output/demo_main_details.json`** - main函数的详细分析
- **`output/demo_summary.json`** - 分析摘要报告
- **`output/demo_stack_main.json`** - main函数的栈使用分析 ⭐
- **`output/demo_stack_summary.json`** - 程序栈使用摘要 ⭐
- **`output/demo_complete.json`** - 完整分析报告（包含所有信息）

## 🚀 快速开始

### 方法1: 自动化演示（推荐）

运行自动化演示脚本，体验所有功能：

```bash
cd demo
python3 run_demo.py
```

演示脚本将自动执行以下步骤：
1. ✅ 检查运行环境
2. 📋 查看ELF文件基本信息
3. 🔍 分析函数调用关系
4. 🛤️ 查找特定调用路径
5. 🎯 分析特定函数详情
6. 📊 生成摘要报告
7. 🏗️ 分析函数栈使用情况 ⭐
8. 📑 执行完整分析

### 方法2: 手动逐步体验

如果你想手动体验每个功能，可以按以下步骤执行：

#### 1. 查看基本信息
```bash
python3 -m elfscope.cli info test_program
```

#### 2. 分析函数调用关系
```bash
python3 -m elfscope.cli analyze test_program -o my_analysis.json
```

#### 3. 查找调用路径
```bash
# 从main到fibonacci_recursive的路径
python3 -m elfscope.cli paths test_program fibonacci_recursive -s main -o fib_paths.json

# 所有调用utility_function_1的路径
python3 -m elfscope.cli paths test_program utility_function_1 -o util_paths.json
```

#### 4. 分析特定函数
```bash
python3 -m elfscope.cli function test_program main -o main_info.json
```

#### 5. 生成摘要报告
```bash
python3 -m elfscope.cli summary test_program -o summary.json
```

#### 6. 栈使用分析 ⭐ 新功能
```bash
# 分析特定函数的栈使用情况
python3 -m elfscope.cli stack test_program main -o output/main_stack.json

# 分析递归函数的栈消耗
python3 -m elfscope.cli stack test_program fibonacci_recursive

# 分析深度调用链的栈使用
python3 -m elfscope.cli stack test_program deep_call_chain_1

# 生成程序的栈使用摘要
python3 -m elfscope.cli stack-summary test_program -o output/stack_summary.json -t 10
```

#### 7. 完整分析
```bash
python3 -m elfscope.cli complete test_program -o output/complete.json
```

## 📊 期望的分析结果

使用我们的测试程序，你应该能看到以下分析结果：

### 📈 统计信息
- **函数总数**: 43个（29个用户函数 + 14个系统函数）
- **调用关系**: 122个
- **递归函数**: 13个
- **调用环**: 15个
- **复杂度**: moderate（中等）

### 🛤️ 调用路径示例
- **最短路径**: main → fibonacci_recursive（1步）
- **最长路径**: main → data_analysis → deep_call_chain_1 → ... → fibonacci_recursive（8步）
- **相互递归**: function_a ⟷ function_b

### 🔍 识别的关键函数
- `fibonacci_recursive` - 递归斐波那契函数
- `factorial_recursive` - 递归阶乘函数
- `function_a`, `function_b` - 相互递归对
- `deep_call_chain_1-5` - 深度调用链
- `utility_function_1-3` - 工具函数组
- `complex_recursive_chain` - 复杂递归链

### 🏗️ 栈使用分析结果 ⭐
- **最大栈消耗函数**: main函数（1232字节）
- **栈消耗分布**:
  - 小栈消耗 (<64B): 15个函数
  - 中等栈消耗 (64-256B): 9个函数
  - 大栈消耗 (256-1KB): 18个函数
  - 巨大栈消耗 (>1KB): 1个函数
- **最大栈消耗路径**: main → main (递归 x10)
- **深度调用链栈消耗**: deep_call_chain_1 (688B) 通过8级调用达到fibonacci_recursive
- **递归函数栈估算**: fibonacci_recursive最大消耗528字节（含递归深度）

## 🔧 测试程序特性

我们的 `test_program.c` 专门设计了以下复杂特性来全面测试 ElfScope：

### 📚 函数调用模式
1. **直接调用** - 简单的函数调用关系
2. **递归调用** - fibonacci_recursive, factorial_recursive
3. **相互递归** - function_a ⟷ function_b
4. **深度调用链** - deep_call_chain_1→2→3→4→5
5. **函数指针调用** - execute_operation通过函数指针调用
6. **条件调用** - 基于运行时条件的分支调用
7. **循环调用关系** - 复杂的环形调用结构

### 🎯 功能模块
- **数学计算模块** - 递归和迭代算法
- **字符串处理模块** - 字符串操作函数组
- **数据处理模块** - 数组处理和分析
- **工具函数模块** - 通用工具函数
- **错误处理模块** - 错误和调试函数

## 📖 查看分析结果

### 使用jq命令（推荐）
```bash
# 查看基本统计信息
jq '.statistics' demo_analysis.json

# 查看所有函数名
jq '.functions | keys[]' demo_analysis.json

# 查看调用路径
jq '.path_analysis.paths[0].path' demo_fibonacci_paths.json

# 查看摘要信息
jq '.' demo_summary.json
```

### 使用文本编辑器
```bash
# 使用你喜欢的编辑器查看JSON文件
nano demo_analysis.json
# 或者
code demo_analysis.json
```

## 🎮 交互式测试

你也可以运行测试程序本身，观察它的行为：

```bash
# 查看帮助
./test_program -h

# 运行不同类型的测试
./test_program -t 1  # 基本函数测试
./test_program -t 2  # 数学函数测试
./test_program -t 3  # 字符串处理测试
./test_program -t 4  # 深度调用链测试
./test_program -t 5  # 数据处理测试

# 详细输出
./test_program -t 2 -v
```

## 🛠️ 自定义测试

### 编译你自己的程序
```bash
# 编译C程序
gcc -o my_program my_program.c -g

# 使用ElfScope分析
python3 -m elfscope.cli analyze my_program -o my_analysis.json
```

### 修改测试程序
你可以修改 `test_program.c` 来添加你自己的测试场景：
1. 编辑 `test_program.c`
2. 重新编译：`gcc -o test_program test_program.c -g`
3. 运行分析：`python3 -m elfscope.cli analyze test_program`

## ❓ 故障排除

### 常见问题

**Q: 运行demo脚本时提示"No module named elfscope"**
A: 确保你在项目根目录或正确设置了PYTHONPATH：
```bash
export PYTHONPATH=/path/to/ElfScope:$PYTHONPATH
```

**Q: 编译test_program失败**
A: 确保安装了gcc：
```bash
sudo apt install gcc  # Ubuntu/Debian
sudo yum install gcc   # CentOS/RHEL
```

**Q: JSON文件太大，难以查看**
A: 使用jq命令查看特定部分：
```bash
jq '.statistics' demo_analysis.json  # 只看统计信息
jq '.functions | keys | length' demo_analysis.json  # 函数数量
```

**Q: 想了解更多命令选项**
A: 使用help命令：
```bash
python3 -m elfscope.cli --help
python3 -m elfscope.cli analyze --help
```

## 📚 进一步学习

- 📖 查看项目根目录的 `README.md` 了解完整的API文档
- 🧪 查看 `tests/` 目录了解更多使用示例
- 🔍 研究 `elfscope/` 源码了解实现细节
- 📊 查看 `TEST_RESULTS.md` 了解详细的测试报告

## 🎉 开始探索！

现在你已经准备好体验 ElfScope 的强大功能了！

1. 🚀 运行 `python3 run_demo.py` 开始自动化演示
2. 🔍 查看生成的JSON分析文件  
3. 🎮 尝试分析你自己的ELF文件
4. 📖 探索更多高级功能

**祝你使用愉快！** 如有问题，欢迎查看项目文档或提交issue。

---

*ElfScope - 让ELF文件分析变得简单而强大！* 🚀
