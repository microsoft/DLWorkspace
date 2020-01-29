/**
 * @typedef {Object} State
 * @property {import('../services/user')} user
 */

const config = require('config')

const frontendConfig = config.has('frontend')
  ? config.get('frontend')
  : Object.create(null)

/** @type {import('koa').Middleware<State>} */
module.exports = (context) => {
  const { user } = context.state
  const parameter = { config: frontendConfig, user }
  context.type = 'js'
  context.body = `bootstrap(${JSON.stringify(parameter)})`
}
