/**
 * @typedef {Object} State
 * @property {import('../services/user')} user
 */

/** @type {import('koa').Middleware<State>} */
module.exports = (context) => {
  const { user } = context.state
  context.type = 'javascript'
  context.body = `bootstrap(${JSON.stringify(user)})`
}
