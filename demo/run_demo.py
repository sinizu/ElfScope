#!/usr/bin/env python3
"""
ElfScope 演示脚本

这个脚本展示了 ElfScope 的所有核心功能：
1. 基本信息查看
2. 完整调用关系分析
3. 调用路径查找
4. 函数详细分析
5. 摘要报告生成
6. 函数栈使用分析 ⭐ 新功能
7. 完整分析

使用方法:
    python3 run_demo.py

注意：确保已经安装了 ElfScope 的所有依赖
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

# 添加 ElfScope 到 Python 路径
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

def print_header(title):
    """打印美观的标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_step(step, description):
    """打印步骤信息"""
    print(f"\n📋 步骤 {step}: {description}")
    print("-" * 50)

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔧 执行: {description}")
    print(f"   命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            print("✅ 成功!")
            if result.stdout.strip():
                print(f"输出:\n{result.stdout}")
        else:
            print("❌ 出错!")
            if result.stderr.strip():
                print(f"错误: {result.stderr}")
    except Exception as e:
        print(f"❌ 执行失败: {e}")
    
    time.sleep(1)  # 让用户有时间查看结果

def display_json_summary(filepath, title):
    """显示JSON文件的摘要信息"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📊 {title} 摘要:")
        
        # 根据文件类型显示不同的摘要信息
        if 'statistics' in data:
            stats = data['statistics']
            print(f"   📈 总函数数: {stats.get('total_functions', 'N/A')}")
            print(f"   📈 调用关系数: {stats.get('total_calls', 'N/A')}")
            print(f"   📈 递归函数: {stats.get('recursive_functions', 'N/A')}")
            print(f"   📈 调用环: {stats.get('cycles', 'N/A')}")
            print(f"   📈 外部函数: {stats.get('external_functions', 'N/A')}")
        
        if 'path_analysis' in data:
            path_stats = data['path_analysis'].get('statistics', {})
            print(f"   🛤️  找到路径: {path_stats.get('total_paths', 'N/A')}")
            print(f"   🛤️  最大深度: {path_stats.get('max_depth', 'N/A')}")
            print(f"   🛤️  平均深度: {path_stats.get('average_depth', 'N/A'):.1f}" 
                  if path_stats.get('average_depth') else "   🛤️  平均深度: N/A")
        
        if 'analysis_summary' in data:
            summary = data['analysis_summary']
            print(f"   📊 函数数: {summary.get('total_functions', 'N/A')}")
            print(f"   📊 调用数: {summary.get('total_calls', 'N/A')}")
            print(f"   📊 复杂度: {data.get('notable_findings', {}).get('complexity', 'N/A')}")
        
        # 栈分析结果显示
        if 'local_stack_frame' in data:
            # 单个函数栈分析
            print(f"   🏗️ 函数: {data.get('function', 'N/A')}")
            print(f"   🏗️ 本地栈帧: {data.get('local_stack_frame', 'N/A')} 字节")
            print(f"   🏗️ 最大栈消耗: {data.get('max_total_stack', 'N/A')} 字节")
            path = data.get('max_stack_call_path', [])
            if path:
                print(f"   🏗️ 调用路径: {' → '.join(path[:3])}{'...' if len(path) > 3 else ''}")
        
        if 'summary' in data and 'max_total_stack_consumption' in data['summary']:
            # 栈摘要结果
            summary = data['summary']
            print(f"   🏗️ 分析函数: {summary.get('total_functions_analyzed', 'N/A')}")
            print(f"   🏗️ 最大栈消耗: {summary.get('max_total_stack_consumption', 'N/A')} 字节")
            print(f"   🏗️ 最大栈函数: {summary.get('function_with_max_total_stack', 'N/A')}")
            heavy_funcs = data.get('heavy_functions', [])
            if heavy_funcs:
                print(f"   🏗️ 高栈消耗函数: {len(heavy_funcs)} 个")
        
    except Exception as e:
        print(f"   ❌ 无法读取 {filepath}: {e}")

def check_prerequisites():
    """检查运行环境"""
    print_header("🔍 环境检查")
    
    # 检查test_program是否存在
    test_program = script_dir / "test_program"
    if not test_program.exists():
        print("❌ 测试程序不存在，尝试重新编译...")
        try:
            subprocess.run(["gcc", "-o", "test_program", "test_program.c", "-g"], 
                         cwd=script_dir, check=True)
            print("✅ 测试程序编译成功!")
        except subprocess.CalledProcessError:
            print("❌ 无法编译测试程序，请确保安装了gcc")
            return False
    else:
        print("✅ 测试程序存在")
    
    # 检查Python依赖
    missing_deps = []
    dependencies = [
        ("elftools", "pyelftools"),
        ("capstone", "capstone"), 
        ("networkx", "networkx"),
        ("click", "click")
    ]
    
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print(f"✅ {module_name} 模块可用")
        except ImportError:
            print(f"❌ {module_name} 模块缺失")
            missing_deps.append(package_name)
    
    if missing_deps:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_deps)}")
        print("\n📋 安装方法:")
        print("方法1 - 使用pip安装:")
        print(f"   pip3 install {' '.join(missing_deps)}")
        print("\n方法2 - 使用系统包管理器 (Ubuntu/Debian):")
        system_packages = []
        for pkg in missing_deps:
            if pkg == "pyelftools":
                system_packages.append("python3-pyelftools")
            elif pkg == "capstone":
                system_packages.append("python3-capstone")
            else:
                system_packages.append(f"python3-{pkg}")
        print(f"   sudo apt install {' '.join(system_packages)}")
        print("\n安装后请重新运行演示脚本。")
        return False
    
    # 检查ElfScope模块
    try:
        import elfscope
        print("✅ ElfScope 模块可用")
    except ImportError as e:
        print(f"❌ ElfScope 模块不可用: {e}")
        print("\n📋 请确保在正确的目录运行此脚本，并且所有依赖已安装。")
        return False
    
    return True

def main():
    """主演示函数"""
    print_header("🚀 ElfScope 全功能演示")
    print("欢迎使用 ElfScope - 专业的 ELF 文件函数调用关系分析工具!")
    print("本演示将展示 ElfScope 的所有核心功能。")
    
    # 环境检查
    if not check_prerequisites():
        print("\n❌ 环境检查失败，演示终止。")
        return
    
    demo_dir = script_dir
    output_dir = demo_dir / "output"
    test_program = "./test_program"
    
    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    
    # 步骤1: 查看基本信息
    print_step(1, "查看测试程序基本信息")
    run_command([
        sys.executable, "-m", "elfscope.cli", 
        "info", str(demo_dir / "test_program")
    ], "获取ELF文件基本信息")
    
    # 步骤2: 完整调用关系分析
    print_step(2, "分析函数调用关系")
    analysis_file = output_dir / "demo_analysis.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "analyze", str(demo_dir / "test_program"),
        "-o", str(analysis_file)
    ], "分析所有函数调用关系")
    
    if analysis_file.exists():
        display_json_summary(analysis_file, "调用关系分析")
    
    # 步骤3: 查找特定调用路径
    print_step(3, "查找调用路径 (main → fibonacci_recursive)")
    paths_file = output_dir / "demo_fibonacci_paths.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "paths", str(demo_dir / "test_program"),
        "fibonacci_recursive", "-s", "main",
        "-o", str(paths_file)
    ], "查找从main到fibonacci_recursive的所有路径")
    
    if paths_file.exists():
        display_json_summary(paths_file, "调用路径分析")
    
    # 步骤4: 查找所有到特定函数的路径
    print_step(4, "查找所有调用路径 (→ utility_function_1)")
    all_paths_file = output_dir / "demo_utility_paths.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "paths", str(demo_dir / "test_program"),
        "utility_function_1",
        "-o", str(all_paths_file)
    ], "查找所有调用utility_function_1的路径")
    
    if all_paths_file.exists():
        display_json_summary(all_paths_file, "所有调用路径")
    
    # 步骤5: 分析特定函数
    print_step(5, "分析特定函数 (main)")
    function_file = output_dir / "demo_main_details.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "function", str(demo_dir / "test_program"),
        "main",
        "-o", str(function_file)
    ], "分析main函数的详细信息")
    
    # 步骤6: 生成摘要报告
    print_step(6, "生成分析摘要")
    summary_file = output_dir / "demo_summary.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "summary", str(demo_dir / "test_program"),
        "-o", str(summary_file)
    ], "生成完整的分析摘要报告")
    
    if summary_file.exists():
        display_json_summary(summary_file, "摘要报告")
    
    # 步骤7: 栈使用分析 ⭐ 新功能
    print_step(7, "分析函数栈使用情况 ⭐ 新功能")
    
    # 7.1: 分析main函数的栈使用
    stack_main_file = output_dir / "demo_stack_main.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "stack", str(demo_dir / "test_program"),
        "main",
        "-o", str(stack_main_file)
    ], "分析main函数的栈使用情况")
    
    if stack_main_file.exists():
        display_json_summary(stack_main_file, "main函数栈分析")
    
    # 7.2: 分析深度调用链的栈使用
    print("   🔍 分析深度调用链栈消耗...")
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "stack", str(demo_dir / "test_program"),
        "deep_call_chain_1"
    ], "分析deep_call_chain_1的栈使用情况（不保存到文件）")
    
    # 7.3: 生成程序栈使用摘要
    stack_summary_file = output_dir / "demo_stack_summary.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "stack-summary", str(demo_dir / "test_program"),
        "-o", str(stack_summary_file),
        "-t", "10"
    ], "生成程序的栈使用摘要（显示栈消耗最大的10个函数）")
    
    if stack_summary_file.exists():
        display_json_summary(stack_summary_file, "栈使用摘要")
    
    # 步骤8: 完整分析
    print_step(8, "完整分析 (包含所有信息)")
    complete_file = output_dir / "demo_complete.json"
    run_command([
        sys.executable, "-m", "elfscope.cli",
        "complete", str(demo_dir / "test_program"),
        "-o", str(complete_file)
    ], "执行完整分析，包含所有信息")
    
    if complete_file.exists():
        display_json_summary(complete_file, "完整分析")
    
    # 演示结束
    print_header("🎉 演示完成!")
    print("\n📁 生成的演示文件:")
    demo_files = [
        ("demo_analysis.json", "完整调用关系分析"),
        ("demo_fibonacci_paths.json", "fibonacci调用路径"),
        ("demo_utility_paths.json", "utility函数调用路径"),
        ("demo_main_details.json", "main函数详细分析"),
        ("demo_summary.json", "分析摘要报告"),
        ("demo_stack_main.json", "main函数栈分析 ⭐"),
        ("demo_stack_summary.json", "程序栈使用摘要 ⭐"),
        ("demo_complete.json", "完整分析报告")
    ]
    
    for filename, description in demo_files:
        filepath = output_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"   ✅ {filename:<25} ({size:,} bytes) - {description}")
        else:
            print(f"   ❌ {filename:<25} - {description} (未生成)")
    
    print(f"\n📂 所有演示文件保存在: {output_dir}")
    print("\n🔍 查看分析结果:")
    print("   - 使用 jq 命令查看JSON文件: jq . output/demo_analysis.json")
    print("   - 使用文本编辑器查看详细内容")
    print("   - 参考 README.md 了解更多使用方法")
    
    print("\n🚀 ElfScope 演示完成! 感谢使用!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  演示被用户终止。")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
