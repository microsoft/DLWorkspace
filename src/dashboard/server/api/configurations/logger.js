const config = require('config')
const logger = require('koa-pino-logger')

/**
 * @param {import('koa')} app
 */
module.exports = (app) => {
  const enabled = app.env !== 'test'
  const prettyPrint = app.env === 'development'
  const middleware = logger({ enabled, prettyPrint })

  // Log the config
  middleware.logger.info(config.util.toObject(), 'App config')

  app.use(middleware)
}
