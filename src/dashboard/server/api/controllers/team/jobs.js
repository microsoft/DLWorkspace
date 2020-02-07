const config = require('config')
const { flatMap, stubArray } = require('lodash')

const Cluster = require('../../services/cluster')

const clusterIds = Object.keys(config.get('clusters'))

const DEFAULT_PRIORITY = 100

/** @type {import('koa').Middleware} */
module.exports = async context => {
  const { teamId } = context.params
  // const offset = Number(context.query.offset) || 0
  const limit = Number(context.query.limit) || 10
  const all = context.query.user === 'all'

  const getClusterJobs = async id => {
    const cluster = new Cluster(context, id)
    const [jobs, jobPriorities] = await Promise.all([
      cluster.getJobs(teamId, all, limit),
      cluster.getJobsPriority().catch(() => Object.create(null)) // Ignore errors
    ])

    jobs.forEach(job => {
      job.cluster = id
      if (job['jobId'] in jobPriorities) {
        job.priority = jobPriorities[job['jobId']]
      } else {
        job.priority = DEFAULT_PRIORITY
      }
    })

    return jobs
  }

  const jobs = flatMap(
    await Promise.all(
      clusterIds.map(
        id => getClusterJobs(id).catch(stubArray)))) // ignore error and return empty array
  jobs.sort((jobA, jobB) => {
    const jobATime = jobA['jobTime']
    const jobBTime = jobB['jobTime']
    const jobADate = new Date(jobATime || 0)
    const jobBDate = new Date(jobBTime || 0)
    return jobBDate - jobADate
  })

  // context.body = jobs.slice(offset, offset + limit)
  context.body = jobs
}
