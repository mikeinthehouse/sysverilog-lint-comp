# syntax=docker/dockerfile:1.14.0

FROM python:slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    jq \
 && LATEST_VERIBLE_VERSION=$(wget -qO- https://api.github.com/repos/chipsalliance/verible/releases/latest | jq -r '.tag_name') \
 && wget https://github.com/chipsalliance/verible/releases/download/${LATEST_VERIBLE_VERSION}/verible-${LATEST_VERIBLE_VERSION}-linux-static-x86_64.tar.gz \
 && mkdir -p /opt/verible \
 && tar -xzf verible-${LATEST_VERIBLE_VERSION}-linux-static-x86_64.tar.gz -C /opt/verible --strip-components=1 \
 && rm -rf verible-${LATEST_VERIBLE_VERSION}-linux-static-x86_64.tar.gz \
 && apt-get purge -y --auto-remove wget jq \
 && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/verible/bin:${PATH}"

RUN verible-verilog-lint --version && verible-verilog-syntax --version

RUN pip install --no-cache-dir fastapi uvicorn

COPY server.py /app/server.py
WORKDIR /app

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
