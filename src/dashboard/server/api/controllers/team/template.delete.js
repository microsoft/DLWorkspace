const config = require('config')

const Cluster = require('../../services/cluster')

const clusterIds = Object.keys(config.get('clusters'))

/** @type {import('koa').Middleware} */
module.exports = async context => {
  const { teamId, templateName } = context.params
  const { database } = context.query

  const deleteClusterTemplate = async id => {
    const cluster = new Cluster(context, id)
    console.log('----> exe!!!')
    return cluster.deleteTemplate(database, teamId, templateName)
  }

  await Promise.all(clusterIds.map(deleteClusterTemplate))

  context.status = 204
}
