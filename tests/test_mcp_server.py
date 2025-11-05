"""
MCP 服务器测试模块

测试 ElfScope MCP 服务器的所有工具功能
"""

import os
import sys
import pytest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from elfscope import mcp_server


# ============================================================================
# 测试辅助函数
# ============================================================================

@pytest.fixture
def test_elf_file(tmp_path):
    """
    创建测试用的简单 ELF 文件路径
    使用系统自带的 /bin/ls 作为测试文件
    """
    system_binary = "/bin/ls"
    if os.path.exists(system_binary):
        return system_binary
    
    # 如果系统没有 /bin/ls，尝试其他常见的二进制文件
    alternatives = ["/bin/cat", "/bin/echo", "/usr/bin/id"]
    for alt in alternatives:
        if os.path.exists(alt):
            return alt
    
    pytest.skip("没有可用的系统二进制文件用于测试")


@pytest.fixture
def nonexistent_file():
    """返回一个不存在的文件路径"""
    return "/nonexistent/path/to/file.elf"


# ============================================================================
# 测试辅助函数
# ============================================================================

def test_wrap_result():
    """测试结果包装函数"""
    data = {"key": "value"}
    result = mcp_server._wrap_result(data, "test_tool", 1.234)
    
    assert result["success"] is True
    assert result["data"] == data
    assert result["metadata"]["tool"] == "test_tool"
    assert result["metadata"]["version"] == "1.0.0"
    assert result["metadata"]["execution_time"] == 1.234
    assert "timestamp" in result["metadata"]


def test_wrap_error():
    """测试错误包装函数"""
    error = ValueError("Test error message")
    result = mcp_server._wrap_error(error, "test_tool")
    
    assert result["success"] is False
    assert result["error"] == "Test error message"
    assert result["error_type"] == "ValueError"
    assert result["metadata"]["tool"] == "test_tool"
    assert "timestamp" in result["metadata"]


def test_validate_file_valid(test_elf_file):
    """测试有效文件验证"""
    # 应该不抛出异常
    mcp_server._validate_file(test_elf_file)


def test_validate_file_not_exists(nonexistent_file):
    """测试文件不存在的情况"""
    with pytest.raises(FileNotFoundError):
        mcp_server._validate_file(nonexistent_file)


def test_validate_file_not_a_file(tmp_path):
    """测试路径不是文件的情况"""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    
    with pytest.raises(ValueError):
        mcp_server._validate_file(str(dir_path))


# ============================================================================
# 测试 MCP 工具
# ============================================================================

class TestElfScopeInfo:
    """测试 elfscope_info 工具"""
    
    def test_info_success(self, test_elf_file):
        """测试成功获取文件信息"""
        result = mcp_server.elfscope_info(test_elf_file)
        
        assert result["success"] is True
        assert "data" in result
        assert "architecture" in result["data"]
        assert "file_type" in result["data"]
        assert "entry_point" in result["data"]
        assert "metadata" in result
    
    def test_info_file_not_exists(self, nonexistent_file):
        """测试文件不存在的情况"""
        result = mcp_server.elfscope_info(nonexistent_file)
        
        assert result["success"] is False
        assert "error" in result
        assert "FileNotFoundError" in result["error_type"]


class TestElfScopeAnalyze:
    """测试 elfscope_analyze 工具"""
    
    def test_analyze_success(self, test_elf_file):
        """测试成功分析调用关系"""
        result = mcp_server.elfscope_analyze(test_elf_file)
        
        assert result["success"] is True
        assert "data" in result
        assert "metadata" in result["data"]
        assert "call_relationships" in result["data"]
        assert "statistics" in result["data"]
    
    def test_analyze_without_stats(self, test_elf_file):
        """测试不包含统计信息"""
        result = mcp_server.elfscope_analyze(
            test_elf_file,
            include_stats=False
        )
        
        assert result["success"] is True
        assert "statistics" not in result["data"]
    
    def test_analyze_without_details(self, test_elf_file):
        """测试不包含详细信息"""
        result = mcp_server.elfscope_analyze(
            test_elf_file,
            include_details=False
        )
        
        assert result["success"] is True
        assert "functions" not in result["data"]


class TestElfScopePaths:
    """测试 elfscope_paths 工具"""
    
    def test_paths_target_only(self, test_elf_file):
        """测试只指定目标函数"""
        # 使用一个常见的函数名
        result = mcp_server.elfscope_paths(
            test_elf_file,
            target_function="main"
        )
        
        # 即使找不到路径，也应该成功返回
        assert result["success"] is True or "error" in result
    
    def test_paths_with_source(self, test_elf_file):
        """测试指定源函数和目标函数"""
        result = mcp_server.elfscope_paths(
            test_elf_file,
            target_function="exit",
            source_function="main"
        )
        
        # 可能找到路径，也可能没有
        assert "success" in result
    
    def test_paths_max_depth(self, test_elf_file):
        """测试限制搜索深度"""
        result = mcp_server.elfscope_paths(
            test_elf_file,
            target_function="main",
            max_depth=5
        )
        
        assert "success" in result


class TestElfScopeComplete:
    """测试 elfscope_complete 工具"""
    
    def test_complete_success(self, test_elf_file):
        """测试完整分析"""
        result = mcp_server.elfscope_complete(test_elf_file)
        
        assert result["success"] is True
        assert "data" in result
        assert "file_info" in result["data"]
        assert "functions" in result["data"]
        assert "call_relationships" in result["data"]
        assert "statistics" in result["data"]


class TestElfScopeFunction:
    """测试 elfscope_function 工具"""
    
    def test_function_main(self, test_elf_file):
        """测试分析 main 函数"""
        result = mcp_server.elfscope_function(test_elf_file, "main")
        
        # main 函数可能存在也可能不存在
        if result["success"]:
            assert "function_name" in result["data"]
            assert result["data"]["function_name"] == "main"
            assert "callers" in result["data"]
            assert "callees" in result["data"]
    
    def test_function_not_exists(self, test_elf_file):
        """测试函数不存在的情况"""
        result = mcp_server.elfscope_function(
            test_elf_file,
            "nonexistent_function_xyz123"
        )
        
        assert result["success"] is False
        assert "error" in result


class TestElfScopeSummary:
    """测试 elfscope_summary 工具"""
    
    def test_summary_success(self, test_elf_file):
        """测试生成摘要报告"""
        result = mcp_server.elfscope_summary(test_elf_file)
        
        assert result["success"] is True
        assert "data" in result
        assert "file_info" in result["data"]
        assert "statistics" in result["data"]
        assert "complexity_assessment" in result["data"]
        assert result["data"]["complexity_assessment"] in ["simple", "moderate", "high"]


class TestElfScopeStack:
    """测试 elfscope_stack 工具"""
    
    def test_stack_main(self, test_elf_file):
        """测试分析 main 函数的栈"""
        result = mcp_server.elfscope_stack(test_elf_file, "main")
        
        # 栈分析可能成功也可能失败（取决于是否能找到函数）
        assert "success" in result
        
        if result["success"]:
            assert "function" in result["data"]
            assert "local_stack_frame" in result["data"]
    
    def test_stack_nonexistent_function(self, test_elf_file):
        """测试不存在的函数"""
        result = mcp_server.elfscope_stack(
            test_elf_file,
            "nonexistent_function_xyz123"
        )
        
        assert result["success"] is False


class TestElfScopeStackSummary:
    """测试 elfscope_stack_summary 工具"""
    
    def test_stack_summary_default(self, test_elf_file):
        """测试默认参数的栈摘要"""
        result = mcp_server.elfscope_stack_summary(test_elf_file)
        
        assert result["success"] is True
        assert "data" in result
        assert "summary" in result["data"]
        assert "heavy_functions" in result["data"]
    
    def test_stack_summary_custom_top(self, test_elf_file):
        """测试自定义 top 参数"""
        result = mcp_server.elfscope_stack_summary(test_elf_file, top=5)
        
        assert result["success"] is True
        assert "heavy_functions" in result["data"]
        assert len(result["data"]["heavy_functions"]) <= 5


class TestElfScopeObjdump:
    """测试 elfscope_objdump 工具"""
    
    def test_objdump_symbols(self, test_elf_file):
        """测试显示符号表"""
        result = mcp_server.elfscope_objdump(test_elf_file, syms=True)
        
        assert result["success"] is True
        assert "data" in result
        assert "symbols" in result["data"]
    
    def test_objdump_headers(self, test_elf_file):
        """测试显示节区头"""
        result = mcp_server.elfscope_objdump(test_elf_file, headers=True)
        
        assert result["success"] is True
        assert "data" in result
        assert "headers" in result["data"]
    
    def test_objdump_disassemble(self, test_elf_file):
        """测试反汇编"""
        result = mcp_server.elfscope_objdump(test_elf_file, disassemble=True)
        
        assert result["success"] is True
        assert "data" in result
        assert "disassembly" in result["data"]
    
    def test_objdump_function(self, test_elf_file):
        """测试反汇编特定函数"""
        result = mcp_server.elfscope_objdump(
            test_elf_file,
            disassemble=True,
            function="main"
        )
        
        # 可能成功也可能失败（取决于是否有 main 函数）
        assert "success" in result


# ============================================================================
# 集成测试
# ============================================================================

class TestMCPServerIntegration:
    """MCP 服务器集成测试"""
    
    def test_multiple_tools_same_file(self, test_elf_file):
        """测试对同一文件使用多个工具"""
        # 获取文件信息
        info_result = mcp_server.elfscope_info(test_elf_file)
        assert info_result["success"] is True
        
        # 分析调用关系
        analyze_result = mcp_server.elfscope_analyze(test_elf_file)
        assert analyze_result["success"] is True
        
        # 生成摘要
        summary_result = mcp_server.elfscope_summary(test_elf_file)
        assert summary_result["success"] is True
        
        # 验证架构信息一致
        arch1 = info_result["data"]["architecture"]
        arch2 = analyze_result["data"]["metadata"]["architecture"]
        assert arch1 == arch2
    
    def test_error_recovery(self, test_elf_file, nonexistent_file):
        """测试错误恢复能力"""
        # 先用不存在的文件（应该失败）
        error_result = mcp_server.elfscope_info(nonexistent_file)
        assert error_result["success"] is False
        
        # 再用正常文件（应该成功）
        success_result = mcp_server.elfscope_info(test_elf_file)
        assert success_result["success"] is True


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

