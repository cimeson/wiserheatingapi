FROM docker.io/python:alpine
COPY . /u/wiser-exporter
WORKDIR /u/wiser-exporter
RUN pip install -r requirements.txt
CMD python prom.py
