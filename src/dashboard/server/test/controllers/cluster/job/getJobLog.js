const axiosist = require('axiosist')
const sinon = require('sinon')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  token: User.generateToken('dlts@example.com').toString('hex')
}

describe('GET /clusters/:clusterId/jobs/:jobId/log', () => {
  it('should return job log', async () => {
    nock('http://universe')
      .get('/GetJobLog?' + new URLSearchParams({ jobId: 'testjob' }))
      .reply(200, {
        log: { "pod": "log" },
        cursor: 0123456789
      })
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/log', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.deepEqual({
      log: { "pod": "log" },
      cursor: 0123456789
    })
  })

  it('should return job log with cursor', async () => {
    nock('http://universe')
      .get('/GetJobLog?' + new URLSearchParams({ jobId: 'testjob', cursor: '1234567890' }))
      .reply(200, {
        log: { "pod": "log" },
        cursor: 9876543210
      })
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/log', {
      params: Object.assign({
        cursor: '1234567890'
      }, userParams)
    })

    response.status.should.equal(200)
    response.data.should.deepEqual({
      log: { "pod": "log" },
      cursor: 9876543210
    })
  })

  it('should return 404 when there is no (more) log', async () => {
    nock('http://universe')
    .get('/GetJobLog?' + new URLSearchParams({ jobId: 'testjob' }))
    .reply(200, {
      log: {},
      cursor: null
    })
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/log', {
      params: userParams
    })

    response.status.should.equal(404)
  })
})
