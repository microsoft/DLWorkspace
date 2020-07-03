const Global = require('../services/global')

/** @type {import('koa').Middleware} */
module.exports = (context, next) => {
  context.state.global = new Global(context)
  return next()
}
