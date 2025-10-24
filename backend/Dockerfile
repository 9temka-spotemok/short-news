FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements and install them first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create scripts directory and copy init scripts
RUN mkdir -p /app/scripts
COPY scripts/init.sh /app/scripts/init.sh
COPY scripts/init_db.py /app/scripts/init_db.py
RUN chmod +x /app/scripts/init.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (Railway will set PORT dynamically)
EXPOSE $PORT

# Start using our main.py with proper PORT handling
CMD ["python", "main.py"]
