# Use Python slim image
FROM python:3.11-slim

# Install Tesseract OCR + OpenCV dependencies
RUN apt-get update && \
    apt-get install -y \
        tesseract-ocr \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all project files into container
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional, for Render)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
