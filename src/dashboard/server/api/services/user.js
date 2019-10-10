const { createHash } = require('crypto')

const config = require('config')
const jwt = require('jsonwebtoken')
const fetch = require('node-fetch')

const Service = require('./service')
const Cluster = require('./cluster')

const sign = config.get('sign')
const winbind = config.has('winbind') ? config.get('winbind') : undefined
const masterToken = config.get('masterToken')
const addGroupLink = config.get('AddGroupLink')
const WikiLink = config.get('WikiLink')
const clusterIds = Object.keys(config.get('clusters'))

class User extends Service {
  /**
   * @param {import('koa').Context} context
   * @param {string} email
   */
  constructor (context, email) {
    super(context)
    this.email = email
  }

  /**
   * @param {import('koa').Context} context
   * @param {object} idToken
   * @return {User}
   */
  static fromIdToken (context, idToken) {
    const user = new User(context, idToken['upn'])
    user.givenName = idToken['given_name']
    user.addGroupLink = addGroupLink
    user.familyName = idToken['family_name']
    user.WikiLink = WikiLink
    return user
  }

  /**
   * @param {import('koa').Context} context
   * @param {object} idToken
   * @return {User}
   */
  static fromToken (context, email, token) {
    const user = new User(context, email)
    const expectedToken = user.token
    const actualToken = Buffer.from(token, 'hex')
    context.assert(expectedToken.equals(actualToken), 403, 'Invalid token')

    return user // No givenName nor familyName here
  }

  /**
   * @param {import('koa').Context} context
   * @param {string} token
   * @return {User}
   */
  static fromCookie (context, token) {
    const payload = jwt.verify(token, sign)
    const user = new User(context, payload['email'])
    user.givenName = payload['givenName']
    user.addGroupLink = addGroupLink
    user.WikiLink = WikiLink
    user.familyName = payload['familyName']
    user.uid = payload['uid']
    user.gid = payload['gid']
    return user
  }

  get token () {
    if (this._token == null) {
      const hash = createHash('md5')
      hash.update(`${this.email}:${masterToken}`)
      this._token = hash.digest()
    }
    return this._token
  }

  async fillIdFromWinbind () {
    if (winbind == null) {
      this.context.log.warn('No winbind server, user will have no uid / gid, and will not sync user info to any cluster.')
      return null
    }

    const params = new URLSearchParams({ userName: this.email })
    const url = `${winbind}/domaininfo/GetUserId?${params}`
    this.context.log.info({ url }, 'Winbind request')
    const response = await fetch(url)
    const data = await response.json()
    this.context.log.info({ data }, 'Winbind response')

    this.uid = data['uid']
    this.gid = data['gid']
    return data
  }

  async addUserToCluster (data) {
    if (data == null) return

    // Fix groups format
    if (Array.isArray(data['groups'])) {
      data['groups'] = JSON.stringify(data['groups'].map(e => String(e)))
    }
    const params = new URLSearchParams(Object.assign({ userName: this.email }, data))
    for (const clusterId of clusterIds) {
      new Cluster(this.context, clusterId).fetch('/AddUser?' + params)
    }
  }

  /**
   * @return {string}
   */
  toCookie () {
    return jwt.sign({
      email: this.email,
      uid: this.uid,
      gid: this.gid,
      familyName: this.familyName,
      givenName: this.givenName,
      addGroupLink: addGroupLink,
      WikiLink: WikiLink
    }, sign)
  }
}

module.exports = User
