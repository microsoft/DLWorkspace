const Koa = require('koa')
const mount = require('koa-mount')

const app = module.exports = new Koa()

require('./configurations/logger')(app)
require('./configurations/config')(app)

app.use(mount('/v2', require('./v2/router').routes()))
app.use(mount('/v2', require('./v2/router').allowedMethods()))

app.use(require('./router').routes())
app.use(require('./router').allowedMethods())

/* istanbul ignore if */
if (require.main === module) {
  app.listen(process.env.PORT || 3000, process.env.HOST)
}
