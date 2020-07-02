const config = require('config')
const fetch = require('node-fetch')

const Service = require('./service')

const restfulapi = config.get('restfulapi')

/**
 * @typedef {Object} State
 * @property {import('./user')} user
 */

class Global extends Service {
  /**
   * @param {import('koa').ParameterizedContext<State>} context
   * @param {string} id
   */
  constructor (context) {
    super(context)
    this.restfulapi = restfulapi
  }

  /**
   * @param {string} templateName
   * @return {Promise<Array>}
   */
  async listKeys () {
    const { user } = this.context.state
    const params = new URLSearchParams({
      username: user.email
    })
    const response = await this.fetch('/PublicKey?' + params)
    const data = await response.json()
    this.context.log.debug({ data }, 'Got keys')
    this.context.assert(response.ok, 502)
    this.context.assert(Array.isArray(data), 502, 'Invalid response')
    return data.map((item) => ({
      id: item['id'],
      name: item['key_title'],
      key: item['public_key'],
      added: item['add_time']
    }))
  }

  /**
   * @param {string} name
   * @param {string} key
   * @return {Promise}
   */
  async addKey (name, key) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      username: user.email,
      key_title: name
    })
    const body = { public_key: key }
    const response = await this.fetch('/PublicKey?' + params, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await response.json()
    this.context.log.debug({ data }, 'Added key with name "%s"', name)
    this.context.assert(response.ok, 502)
    return data
  }

  /**
   * @param {number} id
   * @return {Promise}
   */
  async deleteKey (id) {
    const { user } = this.context.state
    const params = new URLSearchParams({
      username: user.email,
      key_id: id
    })
    const response = await this.fetch('/PublicKey?' + params, {
      method: 'DELETE'
    })
    const text = await response.text()
    this.context.log.debug({ text }, 'Deleted key "%s"', id)
    if (response.status === 404) {
      this.context.throw(404)
    }
    return text
  }

  /**
   * @private
   * @param {string} path
   * @param {import('node-fetch').RequestInit} init
   * @returns {Promise<import('node-fetch').Response>}
   */
  async fetch (path, init) {
    const url = new URL(path, this.restfulapi)
    const begin = Date.now()
    this.context.log.info({ url, init }, 'Global fetch request')
    try {
      const response = await fetch(url, init)
      const duration = Date.now() - begin
      this.context.log.info({ url, init, status: response.status, duration }, 'Global fetch response')
      return response
    } catch (error) {
      const duration = Date.now() - begin
      this.context.log.error({ url, init, error, duration }, 'Global fetch error')
      throw error
    }
  }
}

module.exports = Global
