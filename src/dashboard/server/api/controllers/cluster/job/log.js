const Link = require('http-link-header')

/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state
  const { jobId } = context.params
  const { cursor } = context.query

  const { log, cursor: nextCursor } = await cluster.getJobLog(jobId, cursor)
  context.body = log
  if (nextCursor) {
    const link = new Link()
    const uri = new URL(context.href)
    uri.searchParams.set('cursor', nextCursor)
    link.set({ uri, rel: 'next' })
    context.set('Link', link)
  }
}
