# e2e-test

An end-to-end script for DLTS dashboard.

## Prequesities

- [A Display Server](https://en.wikipedia.org/wiki/Display_server)
- [Node.js](http://nodejs.org/)
- [Yarn](https://yarnpkg.com/)

## Install

```shell
cd src/e2e-test
yarn --production
```

## Configure

Configure using environment variables:

- `PUPPETEER_HEADLESS` set to `false` to disable headless mode.
- `PUPPETEER_USER_DATA_DIR` should be set to a explicit location to persist user sessions.
- `DLTS_DASHBOARD_URL`
- `DLTS_CLUSTER_ID`

dotenv is supported.

## Run

```
yarn start
```
