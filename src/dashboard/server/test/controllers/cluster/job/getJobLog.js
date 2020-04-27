const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  token: User.generateToken('dlts@example.com').toString('hex')
}

describe('GET /clusters/:clusterId/jobs/:jobId/log', function () {
  it('should return job log', async function () {
    nock('http://universe')
      .get('/GetJobLog')
      .query({ jobId: 'testjob', userName: 'dlts@example.com' })
      .reply(200, {
        log: { 'pod': 'log' },
        cursor: 123456789
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/log', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.deepEqual({
      log: { 'pod': 'log' },
      cursor: 123456789
    })
  })

  it('should return job log with cursor', async function () {
    nock('http://universe')
      .get('/GetJobLog')
      .query({ jobId: 'testjob', cursor: '1234567890', userName: 'dlts@example.com' })
      .reply(200, {
        log: { 'pod': 'log' },
        cursor: 987654321
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/log', {
      params: Object.assign({
        cursor: '1234567890'
      }, userParams)
    })

    response.status.should.equal(200)
    response.data.should.deepEqual({
      log: { 'pod': 'log' },
      cursor: 987654321
    })
  })

  it('should return 404 when there is no (more) log', async function () {
    nock('http://universe')
      .get('/GetJobLog')
      .query({ jobId: 'testjob', userName: 'dlts@example.com' })
      .reply(200, {
        log: {},
        cursor: null
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/log', {
      params: userParams
    })

    response.status.should.equal(404)
  })
})
