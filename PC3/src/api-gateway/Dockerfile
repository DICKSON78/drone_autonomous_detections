FROM node:18-slim

WORKDIR /app

COPY package.json ./
RUN npm install --production

COPY app.js ./

EXPOSE 8008

CMD ["node", "app.js"]
