const { invertBy } = require('lodash')

/**
 * @typedef {Object} State
 * @property {import('../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state
  const {
    approved,
    killing,
    pausing,
    queued
  } = invertBy(context.request.body.status)

  /** @param {string[]|undefined} jobIds */
  const valid = (jobIds) => jobIds !== undefined && jobIds.length > 0
  /** @param {Error} error */
  const handleError = (error) => error

  const [
    approvedResponse,
    killingResponse,
    pausingResponse,
    queuedResponse
  ] = await Promise.all([
    valid(approved) ? cluster.setJobsStatus(approved, 'approved').catch(handleError) : undefined,
    valid(killing) ? cluster.setJobsStatus(killing, 'killing').catch(handleError) : undefined,
    valid(pausing) ? cluster.setJobsStatus(pausing, 'pausing').catch(handleError) : undefined,
    valid(queued) ? cluster.setJobsStatus(queued, 'queued').catch(handleError) : undefined
  ])

  context.status = (
    approvedResponse instanceof Error ||
    killingResponse instanceof Error ||
    pausingResponse instanceof Error ||
    queuedResponse instanceof Error
  ) ? 502 : 200

  context.body = {
    approved: approvedResponse,
    killing: killingResponse,
    pausing: pausingResponse,
    queued: queuedResponse
  }
}
