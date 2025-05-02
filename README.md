# comp


## Build Docker Image

```shell
docker build -t tf-dep-planner .
```

## Run Docker Image
Assume your Terraform components are in ./project_dir/components. You must mount this into the container.

```shell
docker run --rm -v "$(pwd)/project_dir:/mnt/project_dir" tf-dep-planner \
  /mnt/project_dir/components/vpc \
  /mnt/project_dir/components/dns \
  /mnt/project_dir/components/bastion \
  /mnt/project_dir/components/app

```

## Output (YAML)

```yaml
execution_plan:
  - [vpc, dns]
  - [bastion]
  - [app]

```

## Usage Examples

### Run with default (all components), local:

```shell
./plan_components.sh
```


### Run with selected components, local:

```shell
./plan_components.sh vpc bastion app
```

### Run with YAML Input, Local:

```shell
./plan_components.sh --yaml config.yaml
```


### Run with Docker:

```shell
USE_DOCKER=true ./plan_components.sh
```

### Run with YAML + Docker:

```shell
USE_DOCKER=true ./plan_components.sh --yaml config.yaml
```

### Example YAML File (components.yaml)

```yaml
components:
  - vpc
  - dns
  - bastion
  - app

```


This script writes the result to execution_plan.yaml and shows it on the terminal.
