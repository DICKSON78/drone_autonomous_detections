FROM node:18-alpine

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    g++ \
    make \
    python3

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

RUN chown -R nodejs:nodejs /app
USER nodejs

EXPOSE 8001
EXPOSE 8081

CMD ["npm", "start"]