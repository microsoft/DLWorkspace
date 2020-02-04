FROM node:erbium


ADD dashboard /usr/src/app/
WORKDIR /usr/src/app

ENV NODE_OPTIONS --max-http-header-size=65536

RUN yarn --frozen-lockfile


RUN ls /usr/src/app/
RUN npm run build

ENV HOST 0.0.0.0
ENV PORT 80

VOLUME /usr/src/app/config
EXPOSE 80

CMD npm start --production
