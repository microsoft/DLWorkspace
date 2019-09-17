const uuid = require('uuid')

/**
 * @typedef {Object} State
 * @property {import('../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state

  const job = Object.assign({}, context.request.body)
  job['familyToken'] = uuid()
  job['isParent'] = 1

  context.body = await cluster.addJob(job)
}
