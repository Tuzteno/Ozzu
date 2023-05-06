FROM python:3.9

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .
COPY .env .

# Expose the application port
EXPOSE 8000



# Start app
CMD ["uvicorn", "core:app", "--host", "0.0.0.0", "--port", "8000"]
