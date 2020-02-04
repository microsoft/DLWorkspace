/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async (context) => {
  const { cluster } = context.state
  const teamId = context.params.teamId
  const limit = Number(context.query.limit) || 10
  const all = context.query.user === 'all'

  const jobs = await cluster.getJobs(teamId, all, limit)
  context.body = jobs
}
