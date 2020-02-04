const { createHash } = require('crypto')

const config = require('config')
const jwt = require('jsonwebtoken')

const Service = require('./service')

const sign = config.get('sign')
const masterToken = config.get('masterToken')

const TOKEN = Symbol('token')

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
    user.familyName = idToken['family_name']
    return user
  }

  /**
   * @param {import('koa').Context} context
   * @param {string} email
   * @param {string} password
   * @return {User}
   */
  static fromPassword (context, email, password) {
    const user = new User(context, email)
    const expectedToken = user.token
    const actualToken = Buffer.from(password, 'hex')
    context.assert(expectedToken.equals(actualToken), 403, 'Invalid token')

    return user // No givenName nor familyName here
  }

  /**
   * @param {import('koa').Context} context
   * @param {string} cookieToken
   * @return {User}
   */
  static fromCookieToken (context, cookieToken) {
    const payload = jwt.verify(cookieToken, sign)
    const user = new User(context, payload['email'])
    user.givenName = payload['givenName']
    user.familyName = payload['familyName']
    user.uid = payload['uid']
    user.gid = payload['gid']
    return user
  }

  /**
   * @param {string} email
   * @return {Buffer}
   */
  static generateToken (email) {
    const hash = createHash('md5')
    hash.update(`${email}:${masterToken}`)
    return hash.digest()
  }

  get token () {
    if (this[TOKEN] == null) {
      this[TOKEN] = User.generateToken(this.email)
    }
    return this[TOKEN]
  }

  /**
   * @return {string}
   */
  toCookieToken () {
    return jwt.sign({
      email: this.email,
      uid: this.uid,
      gid: this.gid,
      familyName: this.familyName,
      givenName: this.givenName
    }, sign)
  }

  toJSON () {
    return {
      email: this.email,
      password: this.token.toString('hex'),
      uid: this.uid,
      gid: this.gid,
      familyName: this.familyName,
      givenName: this.givenName
    }
  }
}

module.exports = User
