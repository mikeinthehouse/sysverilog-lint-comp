# Use a lightweight Python image
FROM python:3.9-slim

# Set environment variables for Verible version and platform
ENV VERIBLE_VERSION=v0.0-3980-gb4e3f5c
ENV VERIBLE_PLATFORM=linux-static-x86_64

# Install required system packages and clean up in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
 && wget https://github.com/chipsalliance/verible/releases/download/${VERIBLE_VERSION}/verible-${VERIBLE_VERSION}-${VERIBLE_PLATFORM}.tar.gz \
 && mkdir /opt/verible \
 && tar -xzf verible-${VERIBLE_VERSION}-${VERIBLE_PLATFORM}.tar.gz -C /opt/verible --strip-components=1 \
 && mv /opt/verible/bin/verible-verilog-lint /usr/local/bin/ \
 && mv /opt/verible/bin/verible-verilog-parse /usr/local/bin/ \
 && rm verible-${VERIBLE_VERSION}-${VERIBLE_PLATFORM}.tar.gz \
 && apt-get purge -y --auto-remove wget \
 && rm -rf /var/lib/apt/lists/*

# Verify Verible installation
RUN verible-verilog-lint --version && verible-verilog-parse --version

# Install Python dependencies without cache
RUN pip install --no-cache-dir fastapi uvicorn

# Copy the server code into the container
COPY server.py /app/server.py
WORKDIR /app

# Expose the port FastAPI will run on
EXPOSE 8080

# Command to run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
