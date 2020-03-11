const Koa = require('koa')
const mount = require('koa-mount')

const app = module.exports = new Koa()

app.use(mount('/api', require('./api')))
app.use(require('./frontend'))

/* istanbul ignore if */
if (require.main === module) {
  const http = require('http')
  const http2 = require('http2')

  const {
    HOST,
    PORT = '3000',
    HTTPS
  } = process.env

  const server = HTTPS
    ? http2.createSecureServer({ allowHTTP1: true })
    : http.createServer()

  if (HTTPS) {
    require('./ssl')(server)
  }

  server.on('request', app.callback())
  server.listen(Number(PORT), HOST)
}
