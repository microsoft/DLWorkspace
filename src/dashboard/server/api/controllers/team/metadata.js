/**
 * @typedef {Object} State
 * @property {import('../../services/cluster')} cluster
 */

const tryParseJSON = (json, empty) => {
  try {
    return JSON.parse(json)
  } catch (e) {
    return empty
  }
}

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
    const { cluster } = context.state
    const { teamId } = context.params
    const quota = await cluster.getQuota()
    if(!quota.hasOwnProperty(teamId))
      context.body = "teamId not found!"
    else{
      const metadataObject = quota[teamId]['resourceMetadata']['gpu']
      const gpus = Object.create(null)
      for (const sku of Object.keys(metadataObject)) {
        gpus['type'] = metadataObject[sku]['gpu_type']
        gpus['per_node'] = metadataObject[sku]['per_node']
      }
      context.body = gpus
    }

  }
  