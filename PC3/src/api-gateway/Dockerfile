FROM node:18-alpine

WORKDIR /app

# Copy local node_modules if available (pre-installed), otherwise run npm install
COPY node_modules /app/node_modules
COPY package.json package-lock.json* ./
RUN if [ ! -d node_modules ]; then npm install --production; fi

COPY src/ ./src/
COPY public/ ./public/

EXPOSE 8008

CMD ["node", "src/app.js"]
