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
    TLS_KEY,
    TLS_CERT
  } = process.env

  const server = TLS_KEY && TLS_CERT
    ? https.createServer({
      key: fs.readFileSync(TLS_KEY),
      cert: fs.readFileSync(TLS_CERT)
    })
    : http.createServer()

  server.on('request', app.callback())
  server.listen(PORT, HOST)
}
