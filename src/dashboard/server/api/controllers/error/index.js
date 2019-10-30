const { readFileSync } = require('fs')
const { join } = require('path')

const image = readFileSync(join(__dirname, 'error.gif'))

/** @type {import('koa').Middleware} */
module.exports = (context) => {
  context.log.error({ error: context.query }, 'frontend error reported')
  context.type = 'gif'
  context.body = image
}
