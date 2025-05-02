import os
import sys
import yaml
import networkx as nx
from collections import deque

def extract_deps(component_path):
    deps = set()
    for root, _, files in os.walk(component_path):
        for file in files:
            if file.endswith(".tf"):
                try:
                    with open(os.path.join(root, file)) as f:
                        for line in f:
                            if "../" in line:
                                parts = line.strip().split("../")
                                if len(parts) > 1:
                                    dep = parts[1].split("/")[0]
                                    deps.add(dep)
                            elif "module." in line:
                                parts = line.strip().split("module.")
                                if len(parts) > 1:
                                    dep = parts[1].split()[0].split('"')[0].split("'")[0]
                                    deps.add(dep)
                except Exception:
                    continue
    return deps

def build_graph(component_dirs):
    graph = nx.DiGraph()
    component_map = {os.path.basename(p.rstrip("/")): p for p in component_dirs}

    for comp, path in component_map.items():
        graph.add_node(comp)
        deps = extract_deps(path)
        for dep in deps:
            if dep in component_map:
                graph.add_edge(dep, comp)
    return graph

def topological_layers(graph):
    in_degree = {node: 0 for node in graph}
    for u in graph:
        for v in graph.successors(u):
            in_degree[v] += 1

    zero_deg = deque([node for node in graph if in_degree[node] == 0])
    layers = []

    while zero_deg:
        layer = list(zero_deg)
        layers.append(sorted(layer))
        next_zero_deg = deque()

        for node in layer:
            for neighbor in graph.successors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_zero_deg.append(neighbor)

        zero_deg = next_zero_deg

    if any(in_degree[node] > 0 for node in graph):
        raise ValueError("Cycle detected!")

    return layers

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: grouped_sort.py <component_path1> <component_path2> ...")
        sys.exit(1)

    component_paths = sys.argv[1:]
    graph = build_graph(component_paths)
    layers = topological_layers(graph)
    print(yaml.dump({"execution_plan": layers}, sort_keys=False))
