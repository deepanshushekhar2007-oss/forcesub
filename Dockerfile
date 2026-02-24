# Base Python image
FROM python:3.11-slim

# Install Tesseract OCR + dependencies
RUN apt-get update && \
    apt-get install -y tesseract-ocr libsm6 libxext6 libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all files to container
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
