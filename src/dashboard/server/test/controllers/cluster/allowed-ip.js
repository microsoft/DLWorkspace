const axiosist = require('axiosist')
const nock = require('nock')

const User = require('../../../api/services/user')
const api = require('../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

describe('/clusters/:clusterId/allowed-ip', function () {
  describe('GET /clusters/:clusterId/allowed-ip', function () {
    it('should response allowed IP', async function () {
      nock('http://universe')
        .get('/AllowRecord?' + new URLSearchParams({
          userName: 'dlts@example.com',
          user: 'dlts@example.com'
        }))
        .reply(200, [
          { ip: '8.8.8.8' }
        ])

      const response = await axiosist(api).get('/clusters/Universe/allowed-ip', {
        params: userParams
      })
      response.status.should.equal(200)
      response.data.should.have.property('ip', '8.8.8.8')
    })

    it('should response 404 when no allowed IP', async function () {
      nock('http://universe')
        .get('/AllowRecord?' + new URLSearchParams({
          userName: 'dlts@example.com',
          user: 'dlts@example.com'
        }))
        .reply(200, [])
      const response = await axiosist(api).get('/clusters/Universe/allowed-ip', {
        params: userParams
      })
      response.status.should.equal(404)
    })
  })

  describe('PUT /clusters/:clusterId/allowed-ip', function () {
    it('should update allowed IP', async function () {
      nock('http://universe')
        .post('/AllowRecord?' + new URLSearchParams({
          userName: 'dlts@example.com',
          user: 'dlts@example.com',
          ip: '8.8.8.8'
        }))
        .reply(204)

      const response = await axiosist(api).put('/clusters/Universe/allowed-ip', {
        ip: '8.8.8.8'
      }, {
        params: userParams
      })
      response.status.should.equal(200)
    })
  })

  describe('DELETE /clusters/:clusterId/allowed-ip', function () {
    it('should update allowed IP', async function () {
      nock('http://universe')
        .delete('/AllowRecord?' + new URLSearchParams({
          userName: 'dlts@example.com',
          user: 'dlts@example.com'
        }))
        .reply(204)

      const response = await axiosist(api).delete('/clusters/Universe/allowed-ip', {
        params: userParams
      })
      response.status.should.equal(200)
    })
  })
})
