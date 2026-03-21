FROM python:3.10-slim

WORKDIR /app

COPY p2p.py .

ENTRYPOINT [ "python", "p2p.py" ]