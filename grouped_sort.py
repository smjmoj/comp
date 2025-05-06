import os
import argparse
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
                        if not isinstance(parsed, dict):
                            continue
                        data_blocks = parsed.get("data", {})
                        trs_blocks = data_blocks.get("terraform_remote_state", {})
                        for block_name, attrs in trs_blocks.items():
                            config = attrs.get("config", {})
                            key = config.get("key")
                            if isinstance(key, str) and key.endswith("/terraform.state"):
                                dep = key.split("/", 1)[0]
                                deps.add(dep)
                                if verbose:
                                    print(f"[DEBUG] {os.path.basename(component_path)} depends on {dep} (from key = '{key}')")
                except Exception as e:
                    if verbose:
                        print(f"[WARN] Could not parse {full_path}: {e}")
    return deps

def build_graph(component_paths, verbose=False):
    graph = nx.DiGraph()
    name_to_path = {}

    for path in component_paths:
        name = os.path.basename(os.path.normpath(path))
        name_to_path[name] = path
        graph.add_node(name)

    for name, path in name_to_path.items():
        deps = extract_remote_state_deps(path, verbose)
        for dep in deps:
            if dep in name_to_path:
                graph.add_edge(dep, name)

    return graph

def topological_groups(graph):
    from collections import defaultdict

    in_deg = dict(graph.in_degree())
    zero_deg = sorted([n for n, deg in in_deg.items() if deg == 0])
    result = []

    while zero_deg:
        result.append(zero_deg)
        next_zero = []
        for node in zero_deg:
            for child in sorted(graph.successors(node)):
                in_deg[child] -= 1
                if in_deg[child] == 0:
                    next_zero.append(child)
        zero_deg = next_zero

    if any(deg > 0 for deg in in_deg.values()):
        raise RuntimeError("Cycle detected")
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Paths to component directories")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    graph = build_graph(args.paths, verbose=args.verbose)

    if args.verbose:
        print("\n[INFO] Graph edges:")
        for u, v in graph.edges:
            print(f"  {u} --> {v}")

    plan = topological_groups(graph)
    print()
    print(yaml.dump({"execution_plan": plan}, sort_keys=False))

if __name__ == "__main__":
    main()
