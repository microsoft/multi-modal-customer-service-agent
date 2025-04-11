# Use Python 3.11 as the base image  
FROM python:3.12
  
# Set the working directory  
WORKDIR /app  

# Install Python dependencies  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
  
# Copy backend source code  
COPY . .  
  
# Expose the backend port  
EXPOSE 8765  
  
# Run the backend application  
CMD ["python", "app.py"]  