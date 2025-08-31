#!/bin/bash

# ElfScope 快速启动演示脚本
# 
# 这个脚本提供了最简单的方式来体验 ElfScope 的功能
# 

set -e  # 遇到错误时退出

echo "🚀 ElfScope 快速演示启动器"
echo "================================="

# 检查是否在正确的目录
if [[ ! -f "test_program.c" ]]; then
    echo "❌ 错误: 请在demo目录中运行此脚本"
    echo "   cd /path/to/ElfScope/demo && ./quick_start.sh"
    exit 1
fi

# 创建输出目录
mkdir -p output

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3，请先安装Python 3"
    exit 1
fi

# 检查GCC（如果需要重新编译）
if [[ ! -f "test_program" ]]; then
    echo "📋 测试程序不存在，正在编译..."
    if ! command -v gcc &> /dev/null; then
        echo "❌ 错误: 未找到gcc，请先安装GCC编译器"
        echo "   Ubuntu/Debian: sudo apt install gcc"
        echo "   CentOS/RHEL: sudo yum install gcc"
        exit 1
    fi
    
    gcc -o test_program test_program.c -g
    echo "✅ 编译完成!"
fi

echo ""
echo "选择演示模式:"
echo "1) 🎬 自动化完整演示 (推荐，约3-4分钟)"
echo "2) ⚡ 快速基本演示 (仅核心功能，约1分钟)"
echo "3) 🏗️ 栈分析演示 (新功能展示，约1分钟) ⭐"
echo "4) 🎯 单步手动演示 (交互式)"
echo "5) 🔍 仅查看程序信息"
echo ""
read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🎬 启动完整自动化演示..."
        python3 run_demo.py
        ;;
    2)
        echo ""
        echo "⚡ 执行快速演示..."
        echo ""
        echo "📋 1/4: 查看程序基本信息"
        python3 -m elfscope.cli info test_program
        
        echo ""
        echo "📋 2/4: 快速分析调用关系"
        python3 -m elfscope.cli analyze test_program -o output/quick_analysis.json
        
        echo ""
        echo "📋 3/4: 查找一个调用路径示例"
        python3 -m elfscope.cli paths test_program fibonacci_recursive -s main -o output/quick_paths.json
        
        echo ""
        echo "📋 4/4: 生成摘要报告"
        python3 -m elfscope.cli summary test_program -o output/quick_summary.json
        
        echo ""
        echo "✅ 快速演示完成!"
        echo "📁 生成的文件:"
        echo "   - output/quick_analysis.json (调用关系分析)"
        echo "   - output/quick_paths.json (调用路径)"
        echo "   - output/quick_summary.json (摘要报告)"
        ;;
    3)
        echo ""
        echo "🏗️ 执行栈分析演示..."
        echo ""
        echo "📋 1/4: 分析main函数栈使用"
        python3 -m elfscope.cli stack test_program main
        
        echo ""
        echo "📋 2/4: 分析递归函数栈消耗"
        python3 -m elfscope.cli stack test_program fibonacci_recursive
        
        echo ""
        echo "📋 3/4: 分析深度调用链栈使用"
        python3 -m elfscope.cli stack test_program deep_call_chain_1
        
        echo ""
        echo "📋 4/4: 生成栈使用摘要"
        python3 -m elfscope.cli stack-summary test_program -o output/stack_demo_summary.json -t 5
        
        echo ""
        echo "✅ 栈分析演示完成!"
        echo "📁 生成的文件:"
        echo "   - output/stack_demo_summary.json (栈使用摘要)"
        echo ""
        echo "🔬 主要发现:"
        echo "   - main函数是最大栈消耗函数 (~1232字节)"
        echo "   - 深度调用链通过8级调用达到fibonacci_recursive"
        echo "   - 递归函数自动检测并估算栈深度"
        ;;
    4)
        echo ""
        echo "🎯 单步演示模式"
        echo "每步执行后按回车继续..."
        
        echo ""
        echo "步骤1: 查看ELF文件基本信息"
        read -p "按回车执行..."
        python3 -m elfscope.cli info test_program
        
        echo ""
        echo "步骤2: 分析函数调用关系"
        read -p "按回车执行..."
        python3 -m elfscope.cli analyze test_program -o output/manual_analysis.json
        
        echo ""
        echo "步骤3: 查找调用路径 (main -> fibonacci_recursive)"
        read -p "按回车执行..."
        python3 -m elfscope.cli paths test_program fibonacci_recursive -s main -o output/manual_paths.json
        
        echo ""
        echo "步骤4: 分析main函数详情"
        read -p "按回车执行..."
        python3 -m elfscope.cli function test_program main -o output/manual_main.json
        
        echo ""
        echo "步骤5: 栈使用分析 ⭐ 新功能"
        read -p "按回车执行栈分析..."
        echo "  分析main函数栈使用:"
        python3 -m elfscope.cli stack test_program main -o output/manual_main_stack.json
        echo ""
        echo "  生成栈使用摘要:"
        python3 -m elfscope.cli stack-summary test_program -o output/manual_stack_summary.json -t 3
        
        echo ""
        echo "✅ 单步演示完成!"
        ;;
    5)
        echo ""
        echo "🔍 查看测试程序信息..."
        echo ""
        echo "📄 ELF文件信息:"
        python3 -m elfscope.cli info test_program
        
        echo ""
        echo "📊 测试程序统计:"
        wc -l test_program.c
        ls -lh test_program
        
        echo ""
        echo "🎮 你可以运行测试程序："
        echo "   ./test_program -h          # 查看帮助"
        echo "   ./test_program -t 2        # 运行数学函数测试"
        echo "   ./test_program -t 2 -v     # 详细输出"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 演示结束!"
echo ""
echo "📖 更多信息:"
echo "   - 查看 README.md 了解详细使用方法"
echo "   - 运行 python3 run_demo.py 体验完整功能"
echo "   - 查看 ../README.md 了解完整API文档"
echo ""
echo "谢谢使用 ElfScope! 🚀"
