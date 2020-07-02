/**
 * @typedef {Object} State
 * @property {import('../services/global')} global
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async (context) => {
  const { global } = context.state
  context.body = await global.listKeys()
}
