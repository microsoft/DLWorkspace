const uuid = require('uuid')

/**
 * @typedef {Object} State
 * @property {import('../../services/cluster')} cluster
 * @property {import('../../services/user')} user
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster, user } = context.state

  const job = Object.assign({}, context.request.body)

  job['userName'] = user.email
  job['familyToken'] = uuid()
  job['isParent'] = 1

  if (job['preemptionAllowed'] == null && cluster.config['preemptableJobByDefault'] != null) {
    job['preemptionAllowed'] = cluster.config['preemptableJobByDefault'] ? 'True' : 'False'
  }

  context.body = await cluster.addJob(job)
}
