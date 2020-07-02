/**
 * @typedef {Object} State
 * @property {import('../services/global')} global
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async (context) => {
  const { keyId } = context.params
  const { global } = context.state
  const id = Number(keyId)
  context.assert(Number.isFinite(id), 400)
  context.body = await global.deleteKey(id)
}
