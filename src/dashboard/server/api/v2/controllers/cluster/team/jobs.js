const DEFAULT_PRIORITY = 100

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

  const [jobs, jobsPriority] = await Promise.all([
    cluster.getJobs(teamId, all, limit),
    all ? (cluster.getJobsPriority()) : Promise.resolve({})
  ])
  if (all) {
    for (const job of jobs) {
      if (job.jobId in jobsPriority) {
        job.priority = jobsPriority[job.jobId]
      } else {
        job.priority = DEFAULT_PRIORITY
      }
    }
  }
  context.body = jobs
}
