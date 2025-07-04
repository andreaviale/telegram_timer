# Use an official Python image as the base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the necessary files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Environment variable for Python logging
ENV PYTHONUNBUFFERED=1

# Start the bot
CMD ["python", "telegram_timer.py"]