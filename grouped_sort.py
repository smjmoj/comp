import os
import hcl2
import yaml
import networkx as nx
import argparse

def extract_remote_state_deps(component_path, verbose=False):
    deps = set()
    for filename in os.listdir(component_path):
        if not filename.endswith(".tf"):
            continue
        filepath = os.path.join(component_path, filename)
        try:
            with open(filepath, "r") as f:
                data = hcl2.load(f)
        except Exception as e:
            if verbose:
                print(f"[WARN] Failed to parse {filepath}: {e}")
            continue

        if "data" in data:
            terraform_remote_state = data["data"]
            # Handle list of entries under 'data'
            if isinstance(terraform_remote_state, list):
                for entry in terraform_remote_state:
                    if "terraform_remote_state" in entry:
                        for dep_name, dep_data in entry["terraform_remote_state"].items():
                            key = dep_data.get("config", {}).get("key")
                            if isinstance(key, str) and key.endswith("/terraform.state"):
                                dep = key.split("/", 1)[0]
                                deps.add(dep)
                                if verbose:
                                    print(f"[DEBUG] {os.path.basename(component_path)} depends on {dep} from key='{key}'")
    return deps

def build_graph(component_dirs, verbose=False):
    graph = nx.DiGraph()
    name_to_path = {}

    for path in component_dirs:
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
    in_deg = dict(graph.in_degree())
    layers = []

    zero_deg = sorted([n for n, d in in_deg.items() if d == 0])
    while zero_deg:
        layers.append(zero_deg)
        next_zero = []
        for node in zero_deg:
            for succ in graph.successors(node):
                in_deg[succ] -= 1
                if in_deg[succ] == 0:
                    next_zero.append(succ)
        zero_deg = sorted(next_zero)

    if any(d > 0 for d in in_deg.values()):
        raise RuntimeError("Cycle detected!")

    return layers

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="List of component directories")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
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
