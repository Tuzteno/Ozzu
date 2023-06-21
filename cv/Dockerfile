# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . /app

# Expose port 80 to the outside world
EXPOSE 5004

# Run app.py when the container launches
CMD ["uvicorn", "cv:app", "--host", "0.0.0.0", "--port", "5004"]
