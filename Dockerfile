# Use a lightweight Python image
FROM python:3.9-slim

# Install required system packages and Verible
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
 && wget https://github.com/chipsalliance/verible/releases/download/v0.0-3860-gf3da2ce6/verible-v0.0-3860-gf3da2ce6-linux-static-x86_64.tar.gz \
 && mkdir -p /opt/verible \
 && tar -xzf verible-v0.0-3860-gf3da2ce6-linux-static-x86_64.tar.gz -C /opt/verible --strip-components=1 \
 && mv /opt/verible/bin/verible-verilog-lint /usr/local/bin/ \
 && mv /opt/verible/bin/verible-verilog-syntax /usr/local/bin/ \
 && rm -rf verible* \
 && apt-get purge -y --auto-remove wget \
 && rm -rf /var/lib/apt/lists/*

# Verify Verible installation
RUN verible-verilog-lint --version && verible-verilog-syntax --version

# Install Python dependencies without cache
RUN pip install --no-cache-dir fastapi uvicorn

# Copy the server code into the container
COPY server.py /app/server.py
WORKDIR /app

# Expose the port FastAPI will run on
EXPOSE 8080

# Command to run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
