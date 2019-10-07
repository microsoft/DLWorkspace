FROM node:dubnium

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

COPY package.json yarn.lock ./
RUN yarn --frozen-lockfile

COPY . .
RUN npm run build

ENV HOST 0.0.0.0
ENV PORT 80

VOLUME /usr/src/app/config
EXPOSE 80

CMD npm start --production
