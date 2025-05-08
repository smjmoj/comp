import os
import hcl2
import yaml
import networkx as nx
import argparse
import re

def extract_remote_state_deps(component_path, verbose=False):
    deps = set()
    for root, _, files in os.walk(component_path):
        for filename in files:
            if not filename.endswith(".tf"):
                continue
            filepath = os.path.join(root, filename)
            found = False

            if verbose:
                print(f"# [CHECK] Scanning {filepath}")

            try:
                with open(filepath, "r") as f:
                    data = hcl2.load(f)
                found = True
            except Exception as e:
                if verbose:
                    print(f"# [WARN] Failed to parse {filepath} with hcl2: {e}")

            if found:
                if "data" in data:
                    entries = data["data"]
                    if isinstance(entries, list):
                        for entry in entries:
                            if "terraform_remote_state" in entry:
                                for dep_name, dep_data in entry["terraform_remote_state"].items():
                                    key = dep_data.get("config", {}).get("key")
                                    if isinstance(key, str) and "/terraform.tfstate" in key:
                                        dep = key.split("/", 1)[0]
                                        deps.add(dep)
                                        if verbose:
                                            print(f"# [HCL2] {os.path.basename(component_path)} depends on {dep} (key='{key}')")

            else:
                # fallback to regex scan
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                    matches = re.findall(r'key\s*=\s*\"(\w+)/terraform\.tfstate\"', content)
                    for dep in matches:
                        deps.add(dep)
                        if verbose:
                            print(f"# [FALLBACK] {os.path.basename(component_path)} regex-detected dependency: {dep}")
                except Exception as e:
                    if verbose:
                        print(f"# [ERROR] Could not fallback scan {filepath}: {e}")

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
def load_components_from_yaml(yaml_file):
    """Load the list of components from the given YAML file."""
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    return set(data.get('components', []))  # Use a set for easy filtering

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="List of component directories")
    parser.add_argument("--yaml", required=True, help="Path to the YAML file containing the component list")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Load components from the YAML file
    components_to_process = load_components_from_yaml(args.yaml)

    # Build the graph and process only the required components
    graph = build_graph(args.paths, verbose=args.verbose)

    if args.verbose:
        print("\n# [INFO] Graph edges:")
        for u, v in graph.edges:
            print(f"#  {u} --> {v}")

    # Generate the topological order of components
    plan = topological_groups(graph)

    # Filter the plan to only include the specified components from the YAML file
    filtered_plan = []
    for group in plan:
        filtered_group = [component for component in group if component in components_to_process]
        if filtered_group:
            filtered_plan.append(filtered_group)

    # Print the filtered plan in square brackets
    print("\n---")
    print("# Components in dependency order; parallel execution groups.")
    print("\nexecution_plan:")
    for group in filtered_plan:
        print(f"  - [{', '.join(group)}]")

if __name__ == "__main__":
    main()
