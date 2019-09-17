const compose = require('koa-compose')
const send = require('koa-send')
const serve = require('koa-static')

const index = (context, next) => {
  if (context.method !== 'GET') { return next() }
  if (context.accepts('html') !== 'html') { return next() }
  return send(context, 'build/index.html')
}

module.exports = compose([
  serve('build'),
  index
])
