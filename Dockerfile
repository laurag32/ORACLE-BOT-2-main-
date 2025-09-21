# Use lightweight Python image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Upgrade pip + setuptools + wheel first
RUN pip install --upgrade pip setuptools wheel

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy all project files into container
COPY . .

# Start the bot
CMD ["python", "bot.py"]
