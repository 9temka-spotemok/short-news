FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy only requirements and install them first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Start using uvicorn from installed path
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
