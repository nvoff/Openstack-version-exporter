FROM python:3.11-slim-bookworm

RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc libpython3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY src /app/src/
WORKDIR /app

RUN chown -R 1000:1000 /app && \
    chmod -R a+r /app && \
    chmod +x /app/src/mainversh.py

USER 1000

CMD ["python", "/app/src/mainversh.py"]
