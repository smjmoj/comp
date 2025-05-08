FROM python:3.10-slim

WORKDIR /mnt

COPY grouped_sort.py .
COPY requirements.txt .

RUN pip install -r requirements.txt


ENTRYPOINT ["python", "grouped_sort.py"]
