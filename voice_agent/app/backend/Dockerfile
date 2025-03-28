FROM python:3.11

WORKDIR /app

# Copy backend source code and data
COPY . .
COPY data/ ./data/

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose the application port
EXPOSE 8765

CMD ["python", "app.py", "--host", "0.0.0.0"]