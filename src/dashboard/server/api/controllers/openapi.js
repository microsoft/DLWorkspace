const { createReadStream } = require('fs')

/** @type {import('koa').Middleware} */
module.exports = context => {
  context.type = 'yaml'
  context.body = createReadStream(require.resolve('../documents/openapi.yaml'))
}
