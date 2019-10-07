/**
 * @typedef {Object} State
 * @property {import('../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  context.body = context.state.cluster.config
}
