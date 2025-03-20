# Use the latest stable Python image
FROM python:slim

# Install required system packages and Verible
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
 && wget https://github.com/chipsalliance/verible/releases/latest/download/verible-linux-static-x86_64.tar.gz \
 && mkdir -p /opt/verible \
 && tar -xzf verible-linux-static-x86_64.tar.gz -C /opt/verible --strip-components=1 \
 && rm -rf verible-linux-static-x86_64.tar.gz \
 && apt-get purge -y --auto-remove wget \
 && rm -rf /var/lib/apt/lists/*

# Add Verible binaries to PATH
ENV PATH="/opt/verible/bin:${PATH}"

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
