/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state
  const { jobId } = context.params

  const { timeout } = context.request.body
  context.body = await cluster.setJobTimeout(jobId, timeout)
}
