const axiosist = require('axiosist')
const jwt = require('jsonwebtoken')
const should = require('should')
const touge = require('tough-cookie')

const api = require('../../api').callback()

/**
 * @param {string} code
 * @returns {string}
 */
const trimBootstrap = (code) => {
  const match = code.match(/^bootstrap\((.*)\)$/)
  return match[1]
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
    const content = JSON.parse(trimBootstrap(response.data))
    should(content).be.have.properties(user)
      .and.have.property('addGroupLink', 'http://add-group/')
  })

  it('should response undefined if unauthenticated', async () => {
    const response = await axiosist(api).get('/bootstrap.js')
    response.headers['content-type'].should.startWith('application/javascript')
    const content = trimBootstrap(response.data)
    should(content).be.equal('undefined')
  })

  it('should response undefined if token is invalid', async () => {
    const user = { email: 'dlts@example.com' }
    const token = jwt.sign(user, 'BadSign')
    const cookie = new touge.Cookie({ key: 'token', value: token })
    const response = await axiosist(api).get('/bootstrap.js', {
      headers: { 'Cookie': cookie.cookieString() }
    })
    response.headers['content-type'].should.startWith('application/javascript')
    const content = trimBootstrap(response.data)
    should(content).be.equal('undefined')
  })
})
