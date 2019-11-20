/**
 * @typedef {Object} State
 * @property {import('../services/user')} user
 */

/** @type {import('koa').Middleware<State>} */
module.exports = context => {
  const { user } = context.state
  context.body = { token: user.token.toString('hex') }
}
