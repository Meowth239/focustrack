FROM python:3.11-slim

WORKDIR /app

# Install SSH client for remote development
RUN apt-get update && apt-get install -y openssh-client && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for the bot (update if different)
EXPOSE 5000

# Run the bot
CMD ["python", "bot.py"]