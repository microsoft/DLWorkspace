const config = require('config')

const Cluster = require('../../services/cluster')

const clusterIds = Object.keys(config.get('clusters'))

/** @type {import('koa').Middleware} */
module.exports = async context => {
  const { teamId, templateName } = context.params
  const { database } = context.query

  const updateClusterTemplate = async id => {
    const cluster = new Cluster(context, id)
    return cluster.updateTemplate(database, teamId, templateName, context.request.body)
  }

  await Promise.all(clusterIds.map(updateClusterTemplate))

  context.status = 204
}
