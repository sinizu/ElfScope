"""
调用路径查找器测试用例
"""

import pytest
from unittest.mock import Mock, MagicMock
import networkx as nx

from elfscope.core.path_finder import PathFinder
from elfscope.core.call_analyzer import CallAnalyzer


class TestPathFinder:
    """路径查找器测试类"""

    @pytest.fixture
    def mock_call_analyzer(self):
        """创建模拟的调用关系分析器"""
        analyzer = Mock(spec=CallAnalyzer)
        analyzer.analyzed = True
        
        # 创建一个简单的调用图
        call_graph = nx.DiGraph()
        call_graph.add_node('main')
        call_graph.add_node('func_a')
        call_graph.add_node('func_b')
        call_graph.add_node('func_c')
        call_graph.add_node('leaf_func')
        
        # 添加调用关系：main -> func_a -> func_b -> leaf_func
        #                      -> func_c -> leaf_func
        call_graph.add_edge('main', 'func_a')
        call_graph.add_edge('main', 'func_c')
        call_graph.add_edge('func_a', 'func_b')
        call_graph.add_edge('func_b', 'leaf_func')
        call_graph.add_edge('func_c', 'leaf_func')
        
        analyzer.call_graph = call_graph
        analyzer.get_call_details.return_value = [
            {
                'from_address': 0x401010,
                'to_address': 0x401020,
                'instruction': 'call 0x401020',
                'type': 'call'
            }
        ]
        
        return analyzer

    def test_init(self, mock_call_analyzer):
        """测试初始化"""
        finder = PathFinder(mock_call_analyzer)
        
        assert finder.call_analyzer == mock_call_analyzer
        assert finder.call_graph == mock_call_analyzer.call_graph

    def test_init_with_unanalyzed(self):
        """测试使用未分析的调用分析器初始化"""
        analyzer = Mock()
        analyzer.analyzed = False
        analyzer.analyze = Mock()
        analyzer.call_graph = nx.DiGraph()
        
        finder = PathFinder(analyzer)
        
        # 应该自动调用 analyze
        analyzer.analyze.assert_called_once()

    def test_find_paths_specific_source(self, mock_call_analyzer):
        """测试查找特定源函数到目标函数的路径"""
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.find_paths(
            target_function='leaf_func',
            source_function='main',
            max_depth=5
        )
        
        assert result['target_function'] == 'leaf_func'
        assert result['source_function'] == 'main'
        assert len(result['paths']) > 0
        
        # 应该找到两条路径
        assert result['statistics']['total_paths'] >= 1

    def test_find_paths_all_sources(self, mock_call_analyzer):
        """测试查找所有可能的源函数到目标函数的路径"""
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.find_paths(
            target_function='leaf_func',
            source_function=None,
            max_depth=5
        )
        
        assert result['target_function'] == 'leaf_func'
        assert result['source_function'] is None
        assert len(result['paths']) > 0

    def test_find_paths_nonexistent_target(self, mock_call_analyzer):
        """测试查找不存在的目标函数"""
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.find_paths(
            target_function='nonexistent_func',
            source_function='main'
        )
        
        assert 'error' in result
        assert len(result['paths']) == 0

    def test_find_shortest_path(self, mock_call_analyzer):
        """测试查找最短路径"""
        finder = PathFinder(mock_call_analyzer)
        
        path = finder.find_shortest_path('main', 'leaf_func')
        
        assert path is not None
        assert path[0] == 'main'
        assert path[-1] == 'leaf_func'
        assert len(path) >= 2

    def test_find_shortest_path_no_path(self, mock_call_analyzer):
        """测试查找不存在的路径"""
        finder = PathFinder(mock_call_analyzer)
        
        # 添加一个孤立的节点
        mock_call_analyzer.call_graph.add_node('isolated_func')
        
        path = finder.find_shortest_path('main', 'isolated_func')
        assert path is None

    def test_find_all_callers(self, mock_call_analyzer):
        """测试查找所有调用者"""
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.find_all_callers('leaf_func', max_depth=3)
        
        assert result['target_function'] == 'leaf_func'
        assert result['total_callers'] > 0
        assert len(result['callers']) > 0
        
        # 检查调用者信息
        caller_names = [caller['function'] for caller in result['callers']]
        assert 'func_b' in caller_names or 'func_c' in caller_names

    def test_analyze_function_reachability(self, mock_call_analyzer):
        """测试函数可达性分析"""
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.analyze_function_reachability('main')
        
        assert result['function'] == 'main'
        assert 'can_reach' in result
        assert 'reachable_from' in result
        assert 'is_leaf' in result
        assert 'is_root' in result
        
        # main 函数应该是根函数（没有调用者）
        assert result['is_root'] == True
        assert result['is_leaf'] == False  # main 调用了其他函数

    def test_analyze_function_reachability_leaf(self, mock_call_analyzer):
        """测试叶子函数的可达性分析"""
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.analyze_function_reachability('leaf_func')
        
        assert result['function'] == 'leaf_func'
        assert result['is_leaf'] == True   # 叶子函数
        assert result['is_root'] == False  # 被其他函数调用

    def test_get_critical_functions(self, mock_call_analyzer):
        """测试识别关键函数"""
        finder = PathFinder(mock_call_analyzer)
        
        critical_functions = finder.get_critical_functions()
        
        assert len(critical_functions) > 0
        
        # 检查返回的数据结构
        func_info = critical_functions[0]
        required_keys = [
            'function', 'in_degree', 'out_degree', 'total_degree',
            'betweenness_centrality', 'is_critical'
        ]
        
        for key in required_keys:
            assert key in func_info

    def test_format_path(self, mock_call_analyzer):
        """测试路径格式化"""
        finder = PathFinder(mock_call_analyzer)
        
        path = ['main', 'func_a', 'func_b', 'leaf_func']
        formatted = finder._format_path(path)
        
        assert formatted['path'] == path
        assert formatted['length'] == 3  # 3 个调用步骤
        assert len(formatted['steps']) == 3
        
        # 检查每个步骤的格式
        step = formatted['steps'][0]
        assert 'step' in step
        assert 'from' in step
        assert 'to' in step
        assert 'calls' in step

    def test_find_paths_with_cycles(self, mock_call_analyzer):
        """测试包含环的路径查找"""
        # 添加一个环
        mock_call_analyzer.call_graph.add_edge('func_b', 'func_a')
        
        finder = PathFinder(mock_call_analyzer)
        
        result = finder.find_paths(
            target_function='leaf_func',
            source_function='main',
            max_depth=8,
            include_cycles=True
        )
        
        # 应该能找到路径，即使有环存在
        assert len(result['paths']) > 0

    def test_find_paths_max_depth_limit(self, mock_call_analyzer):
        """测试最大深度限制"""
        finder = PathFinder(mock_call_analyzer)
        
        # 设置很小的最大深度
        result = finder.find_paths(
            target_function='leaf_func',
            source_function='main',
            max_depth=1
        )
        
        # 应该找不到路径，因为深度限制太小
        assert len(result['paths']) == 0

    def test_recursive_path_finding(self):
        """测试递归调用的路径查找"""
        analyzer = Mock(spec=CallAnalyzer)
        analyzer.analyzed = True
        
        # 创建包含递归的调用图
        call_graph = nx.DiGraph()
        call_graph.add_node('recursive_func')
        call_graph.add_node('helper')
        call_graph.add_edge('recursive_func', 'recursive_func')  # 自递归
        call_graph.add_edge('recursive_func', 'helper')
        
        analyzer.call_graph = call_graph
        analyzer.get_call_details.return_value = []
        
        finder = PathFinder(analyzer)
        
        result = finder.find_paths(
            target_function='helper',
            source_function='recursive_func',
            max_depth=3
        )
        
        assert len(result['paths']) > 0


class TestPathFinderEdgeCases:
    """路径查找器边界情况测试"""
    
    def test_empty_call_graph(self):
        """测试空调用图"""
        analyzer = Mock(spec=CallAnalyzer)
        analyzer.analyzed = True
        analyzer.call_graph = nx.DiGraph()
        analyzer.get_call_details.return_value = []
        
        finder = PathFinder(analyzer)
        
        result = finder.find_paths('nonexistent', 'also_nonexistent')
        assert 'error' in result

    def test_single_node_graph(self):
        """测试只有一个节点的图"""
        analyzer = Mock(spec=CallAnalyzer)
        analyzer.analyzed = True
        
        call_graph = nx.DiGraph()
        call_graph.add_node('single_func')
        
        analyzer.call_graph = call_graph
        analyzer.get_call_details.return_value = []
        
        finder = PathFinder(analyzer)
        
        # 查找自身到自身的路径
        result = finder.find_paths('single_func', 'single_func')
        assert len(result['paths']) == 0  # 没有调用边，所以没有路径

    def test_disconnected_components(self):
        """测试不连通的图"""
        analyzer = Mock(spec=CallAnalyzer)
        analyzer.analyzed = True
        
        call_graph = nx.DiGraph()
        call_graph.add_node('component1_a')
        call_graph.add_node('component1_b')
        call_graph.add_node('component2_a')
        call_graph.add_node('component2_b')
        
        call_graph.add_edge('component1_a', 'component1_b')
        call_graph.add_edge('component2_a', 'component2_b')
        
        analyzer.call_graph = call_graph
        analyzer.get_call_details.return_value = []
        
        finder = PathFinder(analyzer)
        
        # 尝试在不连通的组件之间查找路径
        result = finder.find_paths('component2_b', 'component1_a')
        assert len(result['paths']) == 0
