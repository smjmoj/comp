import os
import hcl2
import networkx as nx
from collections import defaultdict, deque

COMPONENTS_DIR = "./project_dir/components"

def find_components():
    return [d for d in os.listdir(COMPONENTS_DIR) if os.path.isdir(os.path.join(COMPONENTS_DIR, d))]

def parse_tf_files(component_path):
    references = set()
    for root, _, files in os.walk(component_path):
        for file in files:
            if file.endswith(".tf"):
                with open(os.path.join(root, file), 'r') as f:
                    try:
                        data = hcl2.load(f)
                    except Exception:
                        continue

                    if "module" in data:
                        for mod_name, mod_content in data["module"].items():
                            for v in mod_content.values():
                                if isinstance(v, str) and "../" in v:
                                    ref = os.path.basename(v.strip("/"))
                                    references.add(ref)

                    for block_type in ("resource", "module"):
                        if block_type in data:
                            for name, content in data[block_type].items():
                                if "depends_on" in content:
                                    for dep in content["depends_on"]:
                                        if isinstance(dep, str) and "module." in dep:
                                            dep_comp = dep.split(".")[1]
                                            references.add(dep_comp)
    return references

def build_dependency_graph():
    graph = nx.DiGraph()
    components = find_components()

    for comp in components:
        graph.add_node(comp)
        comp_path = os.path.join(COMPONENTS_DIR, comp)
        deps = parse_tf_files(comp_path)
        for dep in deps:
            if dep in components:
                graph.add_edge(dep, comp)

    return graph

def topological_group_sort(graph):
    in_degree = {node: 0 for node in graph}
    for u in graph:
        for v in graph.successors(u):
            in_degree[v] += 1

    zero_deg = deque([node for node in graph if in_degree[node] == 0])
    layers = []

    while zero_deg:
        layer = list(zero_deg)
        layers.append(layer)
        next_zero_deg = deque()

        for node in layer:
            for neighbor in graph.successors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_zero_deg.append(neighbor)

        zero_deg = next_zero_deg

    if any(in_degree[node] > 0 for node in graph):
        raise ValueError("Cycle detected in dependencies!")

    return layers

def main():
    graph = build_dependency_graph()
    try:
        grouped_order = topological_group_sort(graph)
        print("Grouped Execution Plan:")
        for i, group in enumerate(grouped_order):
            print(f"Group {i}: {group}")
    except ValueError as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
