FROM node:22-alpine

WORKDIR /workspace

COPY package.json /workspace/package.json
COPY apps/web/package.json /workspace/apps/web/package.json
COPY packages/shared/package.json /workspace/packages/shared/package.json

RUN npm install

COPY apps/web /workspace/apps/web
COPY packages/shared /workspace/packages/shared

EXPOSE 3000

CMD ["npm", "run", "dev", "--workspace", "@real-estat-map/web", "--", "--hostname", "0.0.0.0", "--port", "3000"]
