const config = require('config')
const { uniqBy, flatMap, stubArray } = require('lodash')

const Cluster = require('../../services/cluster')

const clusterIds = Object.keys(config.get('clusters'))

/** @type {import('koa').Middleware} */
module.exports = async context => {
  const { teamId } = context.params

  const getClusterTemplates = async id => {
    const cluster = new Cluster(context, id)
    return cluster.getTemplates(teamId)
  }

  const templates = flatMap(await Promise.all(
    clusterIds.map(id => getClusterTemplates(id).catch(stubArray)) // ignore error and return empty array
  ))
  const unionedTemplates = uniqBy(templates, 'name')

  context.body = unionedTemplates
}
