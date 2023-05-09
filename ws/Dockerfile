FROM python:3.9-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Copy application code to container
COPY . /app

# Change working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 80 to the outside world
EXPOSE 5002


# Install uvicorn
RUN pip install uvicorn

# Start the application
CMD ["uvicorn", "ws:app", "--host", "0.0.0.0", "--port", "5002"]
