const compose = require('koa-compose')
const bodyparser = require('koa-bodyparser')

const validator = require('../validator')

module.exports = schema => {
  return compose([
    bodyparser({ enableTypes: ['json'] }),
    /** @type {import('koa').Middleware} */
    (context, next) => {
      var valid = validator.validate(schema, context.request.body)
      if (schema === 'job' && (!('team' in context.request.body) || !context.request.body['team'])) {
        if ('vcName' in context.request.body && context.request.body['vcName']) {
          context.request.body.team = context.request.body['vcName']
          valid = validator.validate(schema, context.request.body)
        }
      }

      if (!valid) {
        const message = validator.errors.map(
          error => `${error.dataPath} ${error.message}`
        ).join('\n')
        return context.throw(400, message)
      }
      return next()
    }
  ])
}
