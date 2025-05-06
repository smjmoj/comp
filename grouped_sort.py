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
                        blocks = parsed if isinstance(parsed, list) else [parsed]

                        for block in blocks:
                            if not isinstance(block, dict):
                                continue
                            if "data" in block and "terraform_remote_state" in block["data"]:
                                tfrs_blocks = block["data"]["terraform_remote_state"]
                                for name, attrs in tfrs_blocks.items():
                                    key = None

                                    # Try new style: config = { key = "..." }
                                    if isinstance(attrs, dict):
                                        config = attrs.get("config", {})
                                        if isinstance(config, dict):
                                            key = config.get("key")

                                    if isinstance(key, str) and key.endswith("/terraform.state"):
                                        dep_name = key.split("/", 1)[0]
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
    from collections import defaultdict

    in_degree = dict(graph.in_degree())
    zero_in = [n for n, deg in in_degree.items() if deg == 0]
    grouped = []

    while zero_in:
        grouped.append(sorted(zero_in))
        next_zero_in = []

        for node in zero_in:
            for succ in graph.successors(node):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    next_zero_in.append(succ)

        zero_in = next_zero_in

    if any(deg > 0 for deg in in_degree.values()):
        raise RuntimeError("Cycle detected in dependencies.")

    return grouped


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Group Terraform components by dependency order.")
    parser.add_argument("paths", nargs="+", help="Component paths (e.g. ./components/vpc)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    graph = build_dependency_graph(args.paths, verbose=args.verbose)

    if args.verbose:
        print("\n[INFO] Dependency graph edges:")
        for u, v in graph.edges:
            print(f"  {u} --> {v}")

    execution_layers = topological_grouping(graph)

    print(yaml.dump({"execution_plan": execution_layers}, sort_keys=False))
