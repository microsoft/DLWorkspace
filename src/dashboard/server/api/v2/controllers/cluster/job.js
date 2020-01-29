/** @type {import('koa').Middleware} */
module.exports = async (context) => {
  const { cluster } = context.state
  context.body = await cluster.getJob(context.params.jobId)
}
