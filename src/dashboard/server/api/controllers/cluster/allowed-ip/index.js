/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state
  const ip = await cluster.getAllowedIP()
  if (ip == null) {
    context.status = 404
  } else {
    context.body = ip
  }
}
