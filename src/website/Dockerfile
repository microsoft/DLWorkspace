FROM node:erbium as builder

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

COPY package.json yarn.lock ./
RUN yarn --frozen-lockfile

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /usr/src/app/.docz/dist /usr/share/nginx/html
