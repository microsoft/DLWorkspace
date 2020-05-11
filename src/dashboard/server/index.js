const Koa = require('koa')
const mount = require('koa-mount')

const app = module.exports = new Koa()

app.use(mount('/api', require('./api')))
app.use(require('./frontend'))

/* istanbul ignore if */
if (require.main === module) {
  const http = require('http')
  const http2 = require('http2')
  const liveSecureContext = require('live-secure-context')

  const {
    HOST,
    PORT = 3000,
    SSL_KEY,
    SSL_CERT
  } = process.env

  const server = SSL_KEY && SSL_CERT
    ? http2.createSecureServer({
      allowHTTP1: true
    })
    : http.createServer()
  if (SSL_KEY && SSL_CERT) {
    liveSecureContext(server, {
      key: SSL_KEY,
      cert: SSL_CERT
    })
  }
  server.on('request', app.callback())
  server.listen(PORT, HOST)
}
