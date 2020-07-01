/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async (context) => {
  const { cluster } = context.state
  const { teamId } = context.params

  context.body = await cluster.getTeamMeta(teamId)
}
