const axiosist = require('axiosist')
const jwt = require('jsonwebtoken')
const should = require('should')
const touge = require('tough-cookie')

const api = require('../../api').callback()

/**
 * @param {string} code
 * @returns {string}
 */
const getBootstrapArgument = (code) => {
  const bootstrap = argument => argument
  return new Function('bootstrap', `return ${code}`)(bootstrap)
}

describe('GET /bootstrap.js', () => {
  it('should response user info as JavaScript type', async () => {
    const user = { email: 'dlts@example.com' }
    const token = jwt.sign(user, 'DashboardSign')
    const cookie = new touge.Cookie({ key: 'token', value: token })
    const response = await axiosist(api).get('/bootstrap.js', {
      headers: { 'Cookie': cookie.cookieString() }
    })
    response.headers['content-type'].should.startWith('application/javascript')
    const arg = getBootstrapArgument(response.data)
    arg.config.should.have.property('key', 'value')
    arg.user.should.have.properties(user)
  })

  it('should response undefined if unauthenticated', async () => {
    const response = await axiosist(api).get('/bootstrap.js')
    response.headers['content-type'].should.startWith('application/javascript')
    const arg = getBootstrapArgument(response.data)
    arg.config.should.have.property('key', 'value')
    arg.should.not.have.property('user')
  })

  it('should response undefined if token is invalid', async () => {
    const user = { email: 'dlts@example.com' }
    const token = jwt.sign(user, 'BadSign')
    const cookie = new touge.Cookie({ key: 'token', value: token })
    const response = await axiosist(api).get('/bootstrap.js', {
      headers: { 'Cookie': cookie.cookieString() }
    })
    response.headers['content-type'].should.startWith('application/javascript')
    const arg = getBootstrapArgument(response.data)
    arg.config.should.have.property('key', 'value')
    arg.should.not.have.property('user')
  })
})
