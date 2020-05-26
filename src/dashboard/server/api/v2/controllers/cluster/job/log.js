/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async (context) => {
  const { cluster } = context.state
  const { jobId } = context.params
  context.type = 'text'
  context.attachment(`${jobId}.log`)
  context.body = await cluster.getJobLogStream(jobId)
}
