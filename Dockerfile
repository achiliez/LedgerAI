FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Presidio + spaCy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model for Presidio
RUN python -m spacy download en_core_web_lg

# Copy application code
COPY . .

# Run the bot
CMD ["python", "main.py"]
