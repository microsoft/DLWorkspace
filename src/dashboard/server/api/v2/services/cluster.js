const ClusterV1 = require('../../services/cluster')

/**
 * @typedef {Object} State
 * @property {import('./user')} user
 */

/**
 * @extends {ClusterV1<State>}
 */
class Cluster extends ClusterV1 {
  /**
   * @param {string} teamId
   * @param {boolean} all
   * @param {number} limit
   * @return {Promise<Array>}
   */
  async getJobs (teamId, all, limit) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId,
      jobOwner: all ? 'all' : user.email,
      num: limit
    })
    const response = await this.fetch('/ListJobsV2?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    const jobs = [].concat(
      data['finishedJobs'],
      data['queuedJobs'],
      data['runningJobs'],
      data['visualizationJobs']
    )
    jobs.sort((jobA, jobB) => {
      return Date.parse(jobB['jobTime']) - Date.parse(jobA['jobTime'])
    })
    this.context.log.info('Got %d jobs from %s', jobs.length, this.id)
    return jobs
  }

  /**
   * @param {string} jobId
   * @return {Promise}
   */
  async getJob (jobId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      jobId
    })
    const response = await this.fetch('/GetJobDetailV2?' + params)
    this.context.assert(response.ok, 502)
    const job = await response.json()
    this.context.log.debug('Got job %s', job['jobName'])
    return job
  }
}

module.exports = Cluster
