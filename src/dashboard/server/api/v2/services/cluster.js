const ClusterV1 = require('../../services/cluster')

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

  /**
   * @param {string} jobId
   * @return {Promise<NodeJS.ReadableStream>}
   */
  async getJobLogStream (jobId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      jobId
    })
    const response = await this.fetch('/GetJobRawLog?' + params)
    this.context.assert(response.ok, 502)
    return response.body
  }

  /**
   * @typedef {object} Meta
   * @property {number | null} timeout
   * @property {number | null} interactiveGpu
   * @property {'RF' | 'FIFO'} schedulingPolicy
   */

  /**
   * @param {string} teamId
   * @return {Promise<Meta>}
   */
  async getTeamMeta (teamId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId
    })
    const response = await this.fetch('/VCMeta?' + params)
    this.context.assert(response.ok, 502)
    const meta = await response.json()
    this.context.log.debug({ meta }, 'Got team meta of %s', teamId)
    return {
      timeout: typeof meta['job_max_time_second'] === 'number'
        ? meta['job_max_time_second']
        : null,
      interactiveGpu: typeof meta['interactive_limit'] === 'number'
        ? meta['interactive_limit']
        : null,
      schedulingPolicy: meta['scheduling_policy'] === 'FIFO'
        ? 'FIFO'
        : 'RF'
    }
  }

  /**
   * @param {string} teamId
   * @param {Partial<Meta>} meta
   * @return {Promise}
   */
  async updateTeamMeta (teamId, meta) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId
    })
    const body = Object.create(null)
    if (typeof meta.timeout === 'number') {
      body['job_max_time_second'] = meta.timeout
    } else if (meta.timeout === null) {
      body['job_max_time_second'] = null
    }
    if (typeof meta.interactiveGpu === 'number') {
      body['interactive_limit'] = meta.interactiveGpu
    } else if (meta.interactiveGpu === null) {
      body['interactive_limit'] = null
    }
    if (['RF', 'FIFO'].includes(meta.schedulingPolicy)) {
      body['scheduling_policy'] = meta.schedulingPolicy
    }
    const response = await this.fetch('/VCMeta?' + params, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Update team meta of %s response text', teamId)
    this.context.assert(response.ok, response.status, response.statusText)
  }
}

module.exports = Cluster
