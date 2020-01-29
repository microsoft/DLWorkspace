const { version } = require('../../../../package.json')

/** @type {import('koa').Middleware} */
module.exports = context => {
  context.body = { version }
}
