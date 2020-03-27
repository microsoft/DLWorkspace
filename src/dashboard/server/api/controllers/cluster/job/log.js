/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

const CACHE_CONTROL = 'private, max-age=60'

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state
  const { jobId } = context.params
  const { cursor } = context.query

  context.set('cache-control', CACHE_CONTROL)

  try {
    context.body = await cluster.getJobLog(jobId, cursor)
  } catch (error) {
    if (error.status === 404) {
      error.headers = {'cache-control': CACHE_CONTROL}
    }
    throw error
  }
}
