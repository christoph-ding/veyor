# Use a lightweight, secure Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /container_root

# Copy the requirements manifest first to leverage Docker's layer caching
COPY requirements.txt .

# Install dependencies without caching the installation files to keep the image tiny
RUN pip install --no-cache-dir -r requirements.txt

# Fix import pathing so both Uvicorn and Celery resolve app.* packages
ENV PYTHONPATH=/container_root

# COPY the local 'app' directory into '/container_root/app'
COPY app ./app

# Expose API (8000) and Worker Metrics (8081)
EXPOSE 8000
EXPOSE 8081

# Execute the Uvicorn ASGI server to boot your API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 