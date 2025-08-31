"""
ElfScope 安装脚本
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="elfscope",
    version="1.0.0",
    author="ElfScope Team",
    author_email="elfscope@example.com",
    description="ELF 文件函数调用关系分析工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/elfscope/elfscope",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Debuggers",
        "Topic :: System :: Operating System",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "elfscope=elfscope.cli:main",
        ],
    },
    keywords="elf, binary analysis, reverse engineering, call graph, disassembly",
    project_urls={
        "Bug Reports": "https://github.com/elfscope/elfscope/issues",
        "Source": "https://github.com/elfscope/elfscope",
        "Documentation": "https://elfscope.readthedocs.io/",
    },
)
