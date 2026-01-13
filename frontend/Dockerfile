FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* /app/
RUN npm install

COPY . /app

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
