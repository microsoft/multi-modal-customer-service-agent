FROM node:18

WORKDIR /app

# Copy frontend source code
COPY . .

# Install Node.js dependencies and build the frontend
RUN npm install && npm run build

# Expose port for frontend (adjust if needed)
EXPOSE 5173

CMD ["npm", "run", "dev", "--host"]