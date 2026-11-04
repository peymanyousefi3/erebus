FROM python:3.12-slim
COPY scripts/controller_gateway.py /controller_gateway.py
USER 65534:65534
ENTRYPOINT ["python", "-u", "/controller_gateway.py"]
