import os
import sys
import yaml
import hcl2
import networkx as nx
from collections import deque

def extract_module_deps(component_path):
    deps = set()
    for root, _, files in os.walk(component_path):
        for file in files:
            if file.endswith(".tf"):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        parsed = hcl2.load(f)
                        if "module" in parsed:
                            for mod_name in parsed["module"].keys():
                                deps.add(mod_name)
                except Exception:
                    continue
    return deps

def build_dependency_graph(component_paths):
    name_to_path = {os.path.basename(path.rstrip("/")): path for path in component_paths}
    graph = nx.DiGraph()

    for name, path in name_to_path.items():
        graph.add_node(name)
        deps = extract_module_deps(path)
        for dep in deps:
            if dep in name_to_path:
                graph.add_edge(dep, name)

    return graph

def topological_grouping(graph):
    in_degree = {node: 0 for node in graph}
    for u in graph:
        for v in graph.successors(u):
            in_degree[v] += 1

    queue = deque([n for n in graph if in_degree[n] == 0])
    layers = []

    while queue:
        layer = list(queue)
        layers.append(sorted(layer))
        next_queue = deque()

        for node in layer:
            for neighbor in graph.successors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_queue.append(neighbor)

        queue = next_queue

    if any(in_degree[n] > 0 for n in in_degree):
        raise RuntimeError("Cycle detected in component dependencies!")

    return layers

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: grouped_sort.py <component_path1> <component_path2> ...")
        sys.exit(1)

    paths = sys.argv[1:]
    graph = build_dependency_graph(paths)
    execution_layers = topological_grouping(graph)
    print(yaml.dump({"execution_plan": execution_layers}, sort_keys=False))
