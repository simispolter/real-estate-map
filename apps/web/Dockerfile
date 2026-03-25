FROM node:22-alpine

WORKDIR /workspace

COPY package.json /workspace/package.json
COPY package-lock.json /workspace/package-lock.json
COPY apps/web/package.json /workspace/apps/web/package.json
COPY packages/shared/package.json /workspace/packages/shared/package.json

RUN npm ci

COPY apps/web /workspace/apps/web
COPY packages/shared /workspace/packages/shared
RUN sed -i 's/\r$//' /workspace/apps/web/scripts/docker-dev.sh \
  && chmod +x /workspace/apps/web/scripts/docker-dev.sh

EXPOSE 3000

CMD ["/bin/sh", "/workspace/apps/web/scripts/docker-dev.sh"]
