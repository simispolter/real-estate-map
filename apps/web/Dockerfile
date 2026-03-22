FROM node:22-alpine

WORKDIR /workspace

COPY package.json /workspace/package.json
COPY package-lock.json /workspace/package-lock.json
COPY apps/web/package.json /workspace/apps/web/package.json
COPY packages/shared/package.json /workspace/packages/shared/package.json

RUN npm ci

COPY apps/web /workspace/apps/web
COPY packages/shared /workspace/packages/shared
RUN chmod +x /workspace/apps/web/scripts/docker-dev.sh

EXPOSE 3000

CMD ["npm", "run", "dev", "--workspace", "@real-estat-map/web", "--", "--hostname", "0.0.0.0", "--port", "3000"]
