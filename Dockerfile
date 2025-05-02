FROM python:3.10-slim

WORKDIR /app

COPY grouped_sort.py .

RUN pip install networkx pyyaml python-hcl2

ENTRYPOINT ["python", "grouped_sort.py"]
