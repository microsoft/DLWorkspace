const Koa = require('koa')

const app = module.exports = new Koa()

require('./configurations/logger')(app)
require('./configurations/config')(app)

const router = require('./router')

app.use(router.routes())
app.use(router.allowedMethods())

if (require.main === module) {
  app.listen(process.env.PORT || 3000, process.env.HOST)
}
