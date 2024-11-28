# Use a lightweight Python image
FROM python:3.9-slim

# Install required system packages
RUN apt-get update && apt-get install -y wget

# Install Verible pre-built binaries
RUN wget https://github.com/chipsalliance/verible/releases/download/v0.0-1231-gc34320c/verible-v0.0-1231-gc34320c-Ubuntu-20.04-x86_64.tar.gz \
    && tar -xzf verible-*.tar.gz -C /usr/local/bin --strip-components=1 \
    && rm verible-*.tar.gz

# Install Python dependencies
RUN pip install fastapi uvicorn

# Copy the server code into the container
COPY server.py /app/server.py
WORKDIR /app

# Expose the port FastAPI will run on
EXPOSE 8080

# Command to run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
