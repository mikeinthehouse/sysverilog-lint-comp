# Use a lightweight Python image
FROM python:3.9-slim

# Set environment variables for Verible version and platform
ENV VERIBLE_VERSION=v0.0-3860-gf3da2ce6
ENV VERIBLE_PLATFORM=linux-static-x86_64

# Install required system packages
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Verible pre-built binaries
RUN wget https://github.com/chipsalliance/verible/releases/download/${VERIBLE_VERSION}/verible-${VERIBLE_VERSION}-${VERIBLE_PLATFORM}.tar.gz \
    && tar -xzf verible-${VERIBLE_VERSION}-${VERIBLE_PLATFORM}.tar.gz -C /usr/local/bin --strip-components=1 \
    && rm verible-${VERIBLE_VERSION}-${VERIBLE_PLATFORM}.tar.gz

# Install Python dependencies
RUN pip install fastapi uvicorn

# Copy the server code into the container
COPY server.py /app/server.py
WORKDIR /app

# Expose the port FastAPI will run on
EXPOSE 8080

# Command to run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
