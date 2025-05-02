import os
import sys
import yaml
import hcl2
import networkx as nx
from collections import deque

def extract_remote_state_deps(component_path, verbose=False):
    deps = set()
    for root, _, files in os.walk(component_path):
        for file in files:
            if file.endswith(".tf"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r') as f:
                        parsed = hcl2.load(f)
                        data_blocks = parsed.get("data", {}).get("terraform_remote_state", {})
                        for name, block in data_blocks.items():
                            config = block.get("config", {})
                            key = config.get("key")
                            if isinstance(key, str) and key.endswith("/terraform.state"):
                                dep_name = key.split("/")[0]
                                deps.add(dep_name)
                                if verbose:
                                    print(f"[DEBUG] Found dependency in {component_path}: {dep_name} via key='{key}'")
                except Exception as e:
                    if verbose:
                        print(f"[WARN] Failed to parse {full_path}: {e}")
    return deps

def build_dependency_graph(component_paths, verbose=False):
    name_to_path = {os.path.basename(path.rstrip("/")): path for path in component_paths}
    graph = nx.DiGraph()

    for name, path in name_to_path.items():
        graph.add_node(name)
        deps = extract_remote_state_deps(path, verbose=verbose)
        for dep in deps:
            if dep in name_to_path:
                graph.add_edge(dep, name)
            elif verbose:
                print(f"[WARN] Ignored unknown dependency '{dep}' in '{name}'")

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
    import argparse

    parser = argparse.ArgumentParser(description="Group Terraform components by dependency order.")
    parser.add_argument("paths", nargs="+", help="Component paths (e.g. ./components/vpc)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")

    args = parser.parse_args()
    graph = build_dependency_graph(args.paths, verbose=args.verbose)
    execution_layers = topological_grouping(graph)
    print(yaml.dump({"execution_plan": execution_layers}, sort_keys=False))
