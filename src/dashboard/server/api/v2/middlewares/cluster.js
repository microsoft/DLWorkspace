const Cluster = require('../services/cluster')

/** @type {import('koa-router').IParamMiddleware} */
module.exports = (id, context, next) => {
  context.state.cluster = new Cluster(context, id)
  return next()
}
