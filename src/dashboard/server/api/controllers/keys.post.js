/**
 * @typedef {Object} State
 * @property {import('../services/global')} global
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async (context) => {
  const { global } = context.state
  const { name, key } = context.request.body
  const data = await global.addKey(name, key)
  context.status = 201
  context.set('location', `/keys/${data.id}`)
}
