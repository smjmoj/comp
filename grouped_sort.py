import os
import hcl2
import yaml
import networkx as nx

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
                                for _, attrs in tfrs_blocks.items():
                                    if isinstance(attrs, dict):
                                        config = attrs.get("config", {})
                                        key = config.get("key") if isinstance(config, dict) else None
                                        if isinstance(key, str) and key.endswith("/terraform.state"):
                                            dep_name = key.split("/", 1)[0]
                                            deps.add(dep_name)
                                            if verbose:
                                                print(f"[DEBUG] {os.path.basename(component_path)} depends on {dep_name} (from key = '{key}')")

                except Exception as e:
                    if verbose:
                        print(f"[WARN] Failed to parse {full_path}: {e}")
    return deps

def build_dependency_graph(component_paths, verbose=False):
    graph = nx.DiGraph()
    components = {}

    for path in component_paths:
        name = os.path.basename(os.path.normpath(path))
        components[name] = path
        graph.add_node(name)

    for name, path in components.items():
        deps = extract_remote_state_deps(path, verbose=verbose)
        for dep in deps:
            if dep in components:
                graph.add_edge(dep, name)

    return graph

def topological_grouping(graph):
    from collections import defaultdict

    in_degree = dict(graph.in_degree())
    zero_in = sorted([n for n, deg in in_degree.items() if deg == 0])
    grouped = []

    while zero_in:
        grouped.append(zero_in)
        next_zero = []

        for node in zero_in:
            for succ in sorted(graph.successors(node)):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    next_zero.append(succ)

        zero_in = sorted(next_zero)

    if any(deg > 0 for deg in in_degree.values()):
        raise RuntimeError("Cycle detected")

    return grouped

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="List of component directories")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    graph = build_dependency_graph(args.paths, verbose=args.verbose)

    if args.verbose:
        print("\n[INFO] Graph edges:")
        for u, v in graph.edges:
            print(f"  {u} --> {v}")

    execution_order = topological_grouping(graph)
    print()
    print(yaml.dump({"execution_plan": execution_order}, sort_keys=False))
