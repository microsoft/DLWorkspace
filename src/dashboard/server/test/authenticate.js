const axiosist = require('axiosist')
const nock = require('nock')
const jwt = require('jsonwebtoken')
const touge = require('tough-cookie')

const api = require('../api').callback()

describe('/authenticate', function () {
  describe('GET /authenticate', function () {
    it('should redirect the user to login page.', async function () {
      const response = await axiosist(api).get('/authenticate', {
        maxRedirects: 0
      })
      response.status.should.equal(302)
      const { location } = response.headers
      location.should.be.a.String()
        .and.match(/\b00000000-0000-0000-0000-000000000000\b/)
        .and.match(/\b11111111-1111-1111-1111-111111111111\b/)
    })

    it('should sign the user in with code from active directory', async function () {
      const email = 'dlts@example.com'
      nock('https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000/oauth2')
        .filteringRequestBody(/\bclient_id=11111111-1111-1111-1111-111111111111\b/)
        .filteringRequestBody(/\bcode=000000\b/)
        .post('/token')
        .reply(200, {
          id_token: jwt.sign({ upn: email }, 'fake sign')
        })

      const response = await axiosist(api).get('/authenticate', {
        params: {
          code: '000000'
        },
        maxRedirects: 0
      })
      response.status.should.equal(302)

      /** @type {Array<import('tough-cookie').Cookie>} */
      const cookies = response.headers['set-cookie'].map(touge.Cookie.parse)
      const tokenCookie = cookies.filter((cookie) => cookie.key === 'token')[0]
      tokenCookie.should.be.instanceOf(touge.Cookie)

      const payload = jwt.verify(tokenCookie.value, 'DashboardSign')
      payload.email.should.be.equal(email)
    })

    it('should bring ths user back when authentication failed', async function () {
      const response = await axiosist(api).get('/authenticate', {
        params: {
          error: 'Invalid code'
        },
        maxRedirects: 0
      })
      response.status.should.equal(302)
    })
  })

  describe('GET /authenticate/logout', function () {
    it('should bring user to log out page in active directory', async function () {
      const response = await axiosist(api).get('/authenticate/logout', {
        maxRedirects: 0
      })
      response.status.should.equal(302)
      const { location } = response.headers
      location.should.be.a.String()
        .and.match(/\b00000000-0000-0000-0000-000000000000\b/)
    })
  })
})
