const Koa = require('koa')
const mount = require('koa-mount')

const app = module.exports = new Koa()

app.use(mount('/api', require('./api')))
app.use(require('./frontend'))

/* istanbul ignore if */
if (require.main === module) {
  const http = require('http')
  const http2 = require('http2')
  const fs = require('fs')

  const {
    HOST,
    PORT = 3000,
    SSL_KEY,
    SSL_CERT,
    TRUST_PROXY = false
  } = process.env

  const server = SSL_KEY && SSL_CERT
    ? http2.createSecureServer({
      allowHTTP1: true,
      key: fs.readFileSync(SSL_KEY),
      cert: fs.readFileSync(SSL_CERT)
    })
    : http.createServer()

  app.proxy = Boolean(TRUST_PROXY)

  server.on('request', app.callback())
  server.listen(Number(PORT), HOST)
}
