# Makefile for ElfScope

.PHONY: help install test test-unit test-integration test-cov clean lint format check-deps demo mcp-server test-mcp mcp-example

# 默认目标
help:
	@echo "ElfScope - ELF 文件函数调用关系分析工具"
	@echo ""
	@echo "可用目标："
	@echo "  install        - 安装项目和依赖"
	@echo "  test           - 运行所有测试"
	@echo "  test-unit      - 运行单元测试"
	@echo "  test-integration - 运行集成测试"
	@echo "  test-cov       - 运行测试并生成覆盖率报告"
	@echo "  test-mcp       - 运行 MCP 服务器测试"
	@echo "  lint           - 代码检查"
	@echo "  format         - 代码格式化"
	@echo "  clean          - 清理临时文件"
	@echo "  check-deps     - 检查依赖"
	@echo "  demo           - 运行演示"
	@echo "  mcp-server     - 启动 MCP 服务器"
	@echo "  mcp-example    - 运行 MCP 客户端示例"

# 安装项目
install:
	pip install -e .
	pip install -r requirements.txt

# 运行所有测试
test:
	pytest

# 运行单元测试
test-unit:
	pytest -m unit

# 运行集成测试
test-integration:
	pytest -m integration

# 运行测试并生成覆盖率报告
test-cov:
	pytest --cov=elfscope --cov-report=term-missing --cov-report=html

# 代码检查
lint:
	flake8 elfscope/ --max-line-length=100
	flake8 tests/ --max-line-length=100

# 代码格式化
format:
	black elfscope/
	black tests/

# 清理临时文件
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

# 检查依赖
check-deps:
	pip check
	pip list --outdated

# 运行演示
demo:
	@echo "运行 ElfScope 演示..."
	@echo "1. 查看帮助信息"
	python -m elfscope.cli --help
	@echo ""
	@echo "2. 查看可用命令"
	python -m elfscope.cli analyze --help
	@echo ""
	@echo "3. 如果系统中有 /bin/ls，尝试分析它"
	@if [ -f /bin/ls ]; then \
		echo "分析 /bin/ls 的基本信息:"; \
		python -m elfscope.cli info /bin/ls || true; \
	else \
		echo "/bin/ls 不存在，跳过演示"; \
	fi

# 启动 MCP 服务器
mcp-server:
	@echo "启动 ElfScope MCP 服务器..."
	@echo "服务器将通过 stdio 进行通信"
	@echo "按 Ctrl+C 停止服务器"
	python -m elfscope.mcp_server

# 运行 MCP 测试
test-mcp:
	@echo "运行 MCP 服务器测试..."
	pytest tests/test_mcp_server.py -v

# 运行 MCP 客户端示例
mcp-example:
	@echo "运行 MCP 客户端示例..."
	@if [ -f /bin/ls ]; then \
		python examples/mcp_client_example.py /bin/ls; \
	else \
		echo "错误: /bin/ls 不存在"; \
		echo "请指定一个有效的 ELF 文件路径"; \
	fi
