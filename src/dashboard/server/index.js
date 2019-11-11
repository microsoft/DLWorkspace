const Koa = require('koa')
const mount = require('koa-mount')

const app = module.exports = new Koa()

app.use(mount('/api', require('./api')))
app.use(require('./frontend'))

if (require.main === module) {
  const http = require('http')
  const https = require('https')
  const fs = require('fs')

  const {
    HOST,
    PORT = 3000,
    SSL_KEY,
    SSL_CERT
  } = process.env

  const server = SSL_KEY && SSL_CERT
    ? https.createServer({
      key: fs.readFileSync(SSL_KEY),
      cert: fs.readFileSync(SSL_CERT)
    })
    : http.createServer()

  server.on('request', app.callback())
  server.listen(PORT, HOST)
}
