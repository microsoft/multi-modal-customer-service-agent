# Stage 1: Build the React app  
FROM node:18-alpine AS build  
WORKDIR /app  
  
# Copy package files and install dependencies  
COPY package*.json ./  
RUN npm install  
  
# Copy the frontend source code and build the application  
COPY . .  
RUN npm run build  
  
# Stage 2: Build the dynamic Node.js server image  
FROM node:18-alpine  
WORKDIR /app  
  
# Copy the built frontend assets  
COPY --from=build /app/dist ./dist  
  
# Copy the dynamic server code  
COPY server.cjs ./  
  
# Copy a package.json that includes your production server dependencies (e.g., express)  
# If your frontend/package.json already has express, you can reuse it  
COPY package.json ./  
  
# Install only production dependencies  
RUN npm install --only=production  
  
# Expose port 3000 (the dynamic server listens on this port)  
EXPOSE 3000  
  
CMD ["node", "server.cjs"]  