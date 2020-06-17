const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const setTimeoutParams = new URLSearchParams({
  userName: userParams.email,
  jobId: 'd175'
})

describe('PUT /clusters/:clusterId/jobs/:jobId/timeout', function () {
  it('should return OK if timeout set successfully', async function () {
    nock('http://universe')
      .post('/JobMaxTime?' + setTimeoutParams, { second: 0xD175 })
      .reply(200, {
        message: 'timeout set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/d175/timeout',
      { timeout: 0xD175 }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'timeout set successfully')
  })

  it('should return 502 Bad Gateway error if timeout setting failed', async function () {
    nock('http://universe')
      .post('/JobMaxTime?' + setTimeoutParams, { second: 0xD175 })
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/d175/timeout',
      { timeout: 0xD175 }, { params: userParams })

    response.status.should.equal(502)
  })
})
