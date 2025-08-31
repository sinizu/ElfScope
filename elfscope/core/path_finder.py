"""
调用路径查找模块

该模块提供函数间调用路径的查找功能，包括：
- 查找从父函数到子函数的所有路径
- 查找调用某个函数的所有路径
- 路径优化和去重
"""

from typing import Dict, List, Set, Optional, Any, Generator
import logging
from collections import deque
import networkx as nx

from .call_analyzer import CallAnalyzer


class PathFinder:
    """
    调用路径查找器
    
    基于调用关系图查找函数间的调用路径
    """
    
    def __init__(self, call_analyzer: CallAnalyzer):
        """
        初始化路径查找器
        
        Args:
            call_analyzer: 函数调用关系分析器
        """
        self.call_analyzer = call_analyzer
        
        # 确保已经进行了调用关系分析
        if not call_analyzer.analyzed:
            call_analyzer.analyze()
        
        self.call_graph = call_analyzer.call_graph
    
    def find_paths(self, 
                   target_function: str, 
                   source_function: Optional[str] = None,
                   max_depth: int = 10,
                   include_cycles: bool = False) -> Dict[str, Any]:
        """
        查找到目标函数的调用路径
        
        Args:
            target_function: 目标函数名
            source_function: 源函数名，如果为 None 则查找所有可能的源
            max_depth: 最大搜索深度
            include_cycles: 是否包含存在环的路径
            
        Returns:
            包含路径信息的字典
        """
        if target_function not in self.call_graph:
            return {
                'target_function': target_function,
                'source_function': source_function,
                'paths': [],
                'error': f"目标函数 '{target_function}' 不存在"
            }
        
        result = {
            'target_function': target_function,
            'source_function': source_function,
            'paths': [],
            'statistics': {
                'total_paths': 0,
                'max_depth': 0,
                'min_depth': float('inf'),
                'average_depth': 0
            }
        }
        
        if source_function:
            # 查找特定源函数到目标函数的路径
            paths = self._find_paths_between(source_function, target_function, 
                                           max_depth, include_cycles)
        else:
            # 查找所有可能的路径到目标函数
            paths = self._find_all_paths_to_target(target_function, 
                                                 max_depth, include_cycles)
        
        # 处理和格式化路径
        formatted_paths = []
        depths = []
        
        for path in paths:
            if len(path) > 1:  # 至少包含两个函数的路径
                formatted_path = self._format_path(path)
                formatted_paths.append(formatted_path)
                depths.append(len(path) - 1)  # 路径深度
        
        result['paths'] = formatted_paths
        result['statistics']['total_paths'] = len(formatted_paths)
        
        if depths:
            result['statistics']['max_depth'] = max(depths)
            result['statistics']['min_depth'] = min(depths)
            result['statistics']['average_depth'] = sum(depths) / len(depths)
        
        return result
    
    def _find_paths_between(self, 
                           source: str, 
                           target: str, 
                           max_depth: int,
                           include_cycles: bool) -> List[List[str]]:
        """
        查找两个特定函数之间的路径
        
        Args:
            source: 源函数名
            target: 目标函数名
            max_depth: 最大深度
            include_cycles: 是否包含环
            
        Returns:
            路径列表，每个路径是函数名列表
        """
        if source not in self.call_graph:
            logging.warning(f"源函数 '{source}' 不存在")
            return []
        
        paths = []
        
        try:
            # 使用NetworkX查找所有简单路径
            if include_cycles:
                # 允许环的情况下，限制搜索深度
                for path in self._find_paths_with_cycles(source, target, max_depth):
                    paths.append(path)
            else:
                # 使用简单路径（无环）
                for path in nx.all_simple_paths(self.call_graph, source, target, 
                                              cutoff=max_depth):
                    paths.append(path)
        except nx.NetworkXNoPath:
            # 没有路径
            pass
        except Exception as e:
            logging.warning(f"查找路径时出错: {e}")
        
        return paths
    
    def _find_all_paths_to_target(self, 
                                 target: str, 
                                 max_depth: int,
                                 include_cycles: bool) -> List[List[str]]:
        """
        查找所有到达目标函数的路径
        
        Args:
            target: 目标函数名
            max_depth: 最大深度
            include_cycles: 是否包含环
            
        Returns:
            路径列表
        """
        all_paths = []
        
        # 获取所有可能的源函数（没有调用者的函数，或者用户指定的入口函数）
        potential_sources = []
        
        for node in self.call_graph.nodes:
            if node != target:
                # 检查是否有从该节点到目标的路径
                try:
                    if nx.has_path(self.call_graph, node, target):
                        potential_sources.append(node)
                except:
                    pass
        
        # 从每个潜在源查找路径
        for source in potential_sources:
            paths = self._find_paths_between(source, target, max_depth, include_cycles)
            all_paths.extend(paths)
        
        # 去重（保持路径顺序）
        unique_paths = []
        seen_paths = set()
        
        for path in all_paths:
            path_tuple = tuple(path)
            if path_tuple not in seen_paths:
                seen_paths.add(path_tuple)
                unique_paths.append(path)
        
        return unique_paths
    
    def _find_paths_with_cycles(self, 
                               source: str, 
                               target: str, 
                               max_depth: int) -> Generator[List[str], None, None]:
        """
        使用BFS查找包含环的路径
        
        Args:
            source: 源函数
            target: 目标函数
            max_depth: 最大深度
            
        Yields:
            路径列表
        """
        queue = deque([(source, [source])])
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current == target and len(path) > 1:
                yield path.copy()
                continue
            
            # 探索相邻节点
            for neighbor in self.call_graph.successors(current):
                if len(path) < max_depth:
                    # 允许重复访问，但限制路径中同一函数的出现次数
                    if path.count(neighbor) < 2:  # 最多允许重复一次
                        new_path = path + [neighbor]
                        queue.append((neighbor, new_path))
    
    def _format_path(self, path: List[str]) -> Dict[str, Any]:
        """
        格式化路径信息
        
        Args:
            path: 函数名路径
            
        Returns:
            格式化的路径信息
        """
        formatted_path = {
            'path': path,
            'length': len(path) - 1,  # 调用次数
            'steps': []
        }
        
        # 添加每一步的详细信息
        for i in range(len(path) - 1):
            from_func = path[i]
            to_func = path[i + 1]
            
            # 获取调用详情
            call_details = self.call_analyzer.get_call_details(from_func, to_func)
            
            step = {
                'step': i + 1,
                'from': from_func,
                'to': to_func,
                'calls': call_details
            }
            
            formatted_path['steps'].append(step)
        
        return formatted_path
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        查找两个函数间的最短路径
        
        Args:
            source: 源函数名
            target: 目标函数名
            
        Returns:
            最短路径，如果不存在则返回 None
        """
        if source not in self.call_graph or target not in self.call_graph:
            return None
        
        try:
            path = nx.shortest_path(self.call_graph, source, target)
            return path
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logging.warning(f"查找最短路径时出错: {e}")
            return None
    
    def find_all_callers(self, 
                        target_function: str, 
                        max_depth: int = 5) -> Dict[str, Any]:
        """
        查找所有可能调用目标函数的函数（递归向上查找）
        
        Args:
            target_function: 目标函数名
            max_depth: 最大递归深度
            
        Returns:
            调用者信息
        """
        if target_function not in self.call_graph:
            return {
                'target_function': target_function,
                'callers': [],
                'error': f"目标函数 '{target_function}' 不存在"
            }
        
        all_callers = set()
        caller_paths = {}
        
        def collect_callers(func: str, depth: int, path: List[str]):
            if depth > max_depth:
                return
            
            direct_callers = list(self.call_graph.predecessors(func))
            
            for caller in direct_callers:
                if caller not in path:  # 避免环
                    new_path = [caller] + path
                    all_callers.add(caller)
                    
                    # 记录路径
                    if caller not in caller_paths:
                        caller_paths[caller] = []
                    caller_paths[caller].append(new_path)
                    
                    # 递归查找
                    collect_callers(caller, depth + 1, new_path)
        
        # 从目标函数开始收集调用者
        collect_callers(target_function, 0, [target_function])
        
        # 格式化结果
        callers_info = []
        for caller in sorted(all_callers):
            caller_info = {
                'function': caller,
                'paths_to_target': caller_paths[caller],
                'direct_caller': caller in self.call_graph.predecessors(target_function)
            }
            callers_info.append(caller_info)
        
        return {
            'target_function': target_function,
            'total_callers': len(all_callers),
            'callers': callers_info
        }
    
    def analyze_function_reachability(self, function_name: str) -> Dict[str, Any]:
        """
        分析函数的可达性
        
        Args:
            function_name: 函数名
            
        Returns:
            可达性分析结果
        """
        if function_name not in self.call_graph:
            return {
                'function': function_name,
                'error': f"函数 '{function_name}' 不存在"
            }
        
        # 可以调用的函数
        reachable_from = set()
        try:
            reachable_from = set(nx.descendants(self.call_graph, function_name))
        except Exception as e:
            logging.warning(f"计算可达函数时出错: {e}")
        
        # 可以调用该函数的函数
        reachable_to = set()
        try:
            reachable_to = set(nx.ancestors(self.call_graph, function_name))
        except Exception as e:
            logging.warning(f"计算调用者时出错: {e}")
        
        return {
            'function': function_name,
            'can_reach': {
                'count': len(reachable_from),
                'functions': sorted(list(reachable_from))
            },
            'reachable_from': {
                'count': len(reachable_to),
                'functions': sorted(list(reachable_to))
            },
            'is_leaf': len(reachable_from) == 0,  # 叶子函数（不调用其他函数）
            'is_root': len(reachable_to) == 0     # 根函数（没有被其他函数调用）
        }
    
    def get_critical_functions(self) -> List[Dict[str, Any]]:
        """
        识别关键函数（高度连接的函数）
        
        Returns:
            关键函数列表
        """
        critical_functions = []
        
        for node in self.call_graph.nodes:
            in_degree = self.call_graph.in_degree(node)
            out_degree = self.call_graph.out_degree(node)
            total_degree = in_degree + out_degree
            
            # 计算中心性指标
            betweenness = 0
            try:
                betweenness_centrality = nx.betweenness_centrality(self.call_graph)
                betweenness = betweenness_centrality.get(node, 0)
            except Exception as e:
                logging.warning(f"计算中心性时出错: {e}")
            
            function_info = {
                'function': node,
                'in_degree': in_degree,
                'out_degree': out_degree,
                'total_degree': total_degree,
                'betweenness_centrality': betweenness,
                'is_critical': total_degree > 5 or betweenness > 0.1
            }
            
            critical_functions.append(function_info)
        
        # 按重要性排序
        critical_functions.sort(key=lambda x: (x['total_degree'], x['betweenness_centrality']), 
                               reverse=True)
        
        return critical_functions
