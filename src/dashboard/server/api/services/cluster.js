const config = require('config')
const fetch = require('node-fetch')

const Service = require('./service')

const clustersConfig = config.get('clusters')

/**
 * @typedef {Object} State
 * @property {import('./user')} user
 */

class Cluster extends Service {
  /**
   * @param {import('koa').ParameterizedContext<State>} context
   * @param {string} id
   */
  constructor (context, id) {
    super(context)
    if (id === '.default') {
      id = Object.keys(clustersConfig)[0]
    }
    this.id = id
    this.config = clustersConfig[id]
    context.assert(this.config != null, 404, 'Cluster is not found')
  }

  /**
   * @param {string} teamId
   * @param {boolean} all
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
    const response = await this.fetch('/ListJobs?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    const jobs = [].concat(
      data['finishedJobs'],
      data['queuedJobs'],
      data['runningJobs'],
      data['visualizationJobs']
    )
    this.context.log.debug('Got %d jobs from %s', jobs.length, this.id)
    return jobs
  }

  /**
   * @param {string} jobId
   * @return {Promise}
   */
  async getJob (jobId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email
    })
    const response = await this.fetch('/GetJobDetail?' + params)
    this.context.assert(response.ok, 502)
    const job = await response.json()
    this.context.log.debug('Got job %s', job['jobName'])
    return job
  }

  /**
   * @param {object} job
   * @return {Promise<string>}
   */
  async addJob (job) {
    const response = await this.fetch('/PostJob', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(job)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Submit job response text')
    this.context.assert(response.ok, response.status, response.statusText)
    return text
  }

  /**
   * @param {object} job
   * @return {Promise<{ status: string, message?: string }>}
   */
  async getJobStatus (jobId) {
    const params = new URLSearchParams({ jobId })
    const response = await this.fetch('/GetJobStatus?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.assert(data != null, 404)
    this.context.log.debug({ data }, 'Got job status')
    const status = { status: data['jobStatus'] }
    if (data['errorMsg']) {
      status.message = data['errorMsg']
    }
    return status
  }

  /**
   * @param {string} jobId
   * @param {'approved'|'killing'|'pausing'|'queued'} status
   * @return {Promise<string>}
   */
  async setJobStatus (jobId, status) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email
    })
    if (status === 'approved') {
      const response = await this.fetch('/ApproveJob?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Approve job response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else if (status === 'killing') {
      const response = await this.fetch('/KillJob?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Kill job response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else if (status === 'pausing') {
      const response = await this.fetch('/PauseJob?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Pause job response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else if (status === 'queued') { // resume
      const response = await this.fetch('/ResumeJob?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Resume job response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else {
      this.context.throw(400, 'Invalid status')
    }
  }

  /**
   * @param {string[]} jobIds
   * @param {'approved'|'killing'|'pausing'|'queued'} status
   * @return {Promise<string>}
   */
  async setJobsStatus (jobIds, status) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobIds: jobIds.join(','),
      userName: user.email
    })
    if (status === 'approved') {
      const response = await this.fetch('/ApproveJobs?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Approve jobs response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else if (status === 'killing') {
      const response = await this.fetch('/KillJobs?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Kill jobs response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else if (status === 'pausing') {
      const response = await this.fetch('/PauseJobs?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Pause jobs response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else if (status === 'queued') { // resume
      const response = await this.fetch('/ResumeJobs?' + params)
      const text = await response.text()
      this.context.log.debug({ text }, 'Resume jobs response')
      this.context.assert(response.ok, response.status, response.statusText)
      return text
    } else {
      this.context.throw(400, 'Invalid status')
    }
  }

  /**
   * @param {string} jobId
   * @param {string} name
   */
  async setJobName (jobId, name) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      jobId
    })
    const body = { name }
    const response = await this.fetch('/JobName?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Set name %d of job "%s"', name, jobId)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @return {Promise<object>}
   */
  async getJobsPriority () {
    const response = await this.fetch('/jobs/priorities')
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.log.debug('Got priority of %d jobs', Object.keys(data).length)
    return data
  }

  /**
   * @param {string} jobId
   * @param {number} priority
   * @return {Promise}
   */
  async setJobPriorty (jobId, priority) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email
    })
    const body = { [jobId]: priority }
    const response = await this.fetch('/jobs/priorities?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Set priority %d of job "%s"', priority, jobId)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @param {string} jobId
   * @param {boolean} isExempted
   * @return {Promise}
   */
  async setJobExemption (jobId, isExempted) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email
    })
    const body = { 'isExempted': isExempted }
    const response = await this.fetch('/GpuIdleKillExemption?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Set isExempted %s of job "%s"', isExempted.toString(), jobId)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @param {string} jobId
   * @param {number|null} timeout
   * @return {Promise}
   */
  async setJobTimeout (jobId, timeout) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      jobId
    })
    const body = { second: timeout }
    const response = await this.fetch('/JobMaxTime?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Set timeout %d of job "%s"', timeout, jobId)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @param {string} jobId
   * @param {string?} cursor
   * @return {Promise<{log: string, cursor: number}>}
   */
  async getJobLog (jobId, cursor) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email
    })
    if (cursor !== undefined) {
      params.set('cursor', cursor)
    }
    const response = await this.fetch('/GetJobLog?' + params)
    const { log, cursor: nextCursor } = await response.json()
    this.context.assert(Object.keys(log).length > 0, 404)
    return { log, cursor: nextCursor }
  }

  /**
   * @return {Promise<Array>}
   */
  async getTeams () {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email
    })

    const response = await this.fetch('/ListVCs?' + params)
    const data = await response.json()
    this.context.log.debug(data, 'Listed VC')

    return data['result']
  }

  /**
   * @param {string} teamId
   * @return {Promise}
   */
  async getTeam (teamId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId
    })
    const response = await this.fetch('/GetVC?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.assert(data != null, 404, 'Team is not found')
    return data
  }

  /**
   * @param {string} jobId
   * @return {Promise<Array>}
   */
  async getCommands (jobId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email
    })
    const response = await this.fetch('/GetCommands?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.log.debug(data, 'Got commands')
    return data
  }

  /**
   * @param {string} jobId
   * @param {string} command
   * @return {Promise<string>}
   */
  async addCommand (jobId, command) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email,
      command
    })

    const response = await this.fetch('/AddCommand?' + params)
    const text = await response.text()
    this.context.log.debug({ text }, 'Added command "%s" to "%s"', command, jobId)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @param {string} jobId
   * @returns {Promise}
   */
  async getEndpoints (jobId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      jobId,
      userName: user.email
    })

    const response = await this.fetch('/endpoints?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.log.debug(data, 'Got endpoints')

    return data
  }

  /**
   * @param {string} jobId
   * @param {Array} endpoints
   * @returns {Promise<string>}
   */
  async addEndpoint (jobId, endpoints) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email
    })
    const body = { jobId, endpoints }
    const response = await this.fetch('/endpoints?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Added endpoints %o to "%s"', endpoints, jobId)
    if (response.status === 403) {
      this.context.status = 403
    } else {
      this.context.assert(response.ok, 502)
    }
    return text
  }

  /**
   * @param {string} teamId
   * @returns {Promise}
   */
  async getTemplates (teamId) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId
    })
    const response = await this.fetch('/templates?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.log.debug({ data }, 'Got templates from %s', this.id)
    return data
  }

  /**
   * @param {string} templateName
   * @param {object} template
   * @return {Promise<string>}
   */
  async updateTemplate (database, teamId, templateName, template) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId,
      database: {
        user: 'user',
        team: 'vc'
      }[database] || 'user',
      templateName
    })
    const response = await this.fetch('/templates?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(template)
    })
    const text = await response.text()
    this.context.log.debug({ template, text }, 'Updated template %s in %s', templateName, this.id)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @param {string} templateName
   * @return {Promise<string>}
   */
  async deleteTemplate (database, teamId, templateName) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      vcName: teamId,
      database: 'user',
      templateName
    })
    const response = await this.fetch('/templates?' + params, {
      method: 'DELETE'
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Deleted template %s in %s', templateName, this.id)
    this.context.assert(response.ok, 502)
    return text
  }

  /**
   * @return {Promise}
   */
  async getAllowedIP () {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      user: user.email
    })
    const response = await this.fetch('/AllowRecord?' + params)
    this.context.assert(response.ok, 502)
    const data = await response.json()
    this.context.log.debug({ data }, 'Got allowed ip for %s', user.email)
    return data[0]
  }

  /**
   * @param {string} ip
   * @return {Promise}
   */
  async updateAllowedIP (ip) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      user: user.email,
      ip
    })
    const response = await this.fetch('/AllowRecord?' + params, {
      method: 'POST'
    })
    this.context.assert(response.ok, 502)
    const text = await response.text()
    this.context.log.debug({ text }, 'Updated allowed ip for %s', user.email)
    return text
  }

  /**
   * @return {Promise}
   */
  async deleteAllowedIP () {
    const { user } = this.context.state
    const params = new URLSearchParams({
      userName: user.email,
      user: user.email
    })
    const response = await this.fetch('/AllowRecord?' + params, {
      method: 'DELETE'
    })
    this.context.assert(response.ok, 502)
    const text = await response.text()
    this.context.log.debug({ text }, 'Deleted allowed ip for %s', user.email)
    return text
  }

  /**
   * @return {Promise<object>}
   */
  async getQuota () {
    const { user } = this.context.state
    const params = new URLSearchParams({ userName: user.email })
    const response = await this.fetch('/ResourceQuota?' + params)
    this.context.assert(response.ok, response.status)
    const data = await response.json()
    this.context.log.debug({ data }, 'Got cluster quota')
    return data
  }

  /**
   * @param {object} quota
   * @return {Promise}
   */
  async updateQuota (quota) {
    const { user } = this.context.state
    const params = new URLSearchParams({ userName: user.email })
    const response = await this.fetch('/ResourceQuota?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(quota)
    })
    this.context.assert(response.ok, response.status)
    const text = await response.text()
    this.context.log.debug({ text }, 'Updated cluster quota')
    return text
  }

  /**
   * @private
   * @param {string} path
   * @param {import('node-fetch').RequestInit} init
   * @returns {Promise<import('node-fetch').Response>}
   */
  async fetch (path, init) {
    const url = new URL(path, this.config.restfulapi)
    const begin = Date.now()
    this.context.log.info({ url, init }, 'Cluster fetch request')
    try {
      const response = await fetch(url, init)
      const duration = Date.now() - begin
      this.context.log.info({ url, init, status: response.status, duration }, 'Cluster fetch response')
      return response
    } catch (error) {
      const duration = Date.now() - begin
      this.context.log.error({ url, init, error, duration }, 'Cluster fetch error')
      throw error
    }
  }
}

module.exports = Cluster
