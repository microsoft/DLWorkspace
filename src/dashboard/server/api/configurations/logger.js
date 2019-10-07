const config = require('config')
const logger = require('koa-pino-logger')

/**
 * @param {import('koa')} app
 */
module.exports = (app) => {
  const prettyPrint = app.env === 'development'
  const middleware = logger({ prettyPrint })

  // Log the config
  middleware.logger.info(config.util.toObject(), 'App config')

  app.use(middleware)
}
