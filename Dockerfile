# Use lightweight official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /workspace

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for Docker caching layer optimization
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure directory for SQLite database and uploads exist
RUN mkdir -p instance app/static/uploads

# Expose server port
EXPOSE 5000

# Start WSGI Server (Gunicorn) binding to port 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
