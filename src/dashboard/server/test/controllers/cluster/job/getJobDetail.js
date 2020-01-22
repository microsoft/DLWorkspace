const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

// search params for getJob, getCommands and getEndpoints
const getJobParams = new URLSearchParams({
  jobId: 'testjob',
  userName: userParams.email
})

// search params for getJobStatus
const getJobStatusParams = new URLSearchParams({
  jobId: 'testjob'
})

describe('GET /clusters/:clusterId/jobs/:jobId', () => {
  it('should return job detail', async () => {
    nock('http://universe')
      .get('/GetJobDetail?' + getJobParams)
      .reply(200, {
        message: 'job detail retrieved'
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'job detail retrieved')
  })

  it('should return 502 Bad Gateway Error when the job does not exist', async () => {
    nock('http://universe')
      .get('/GetJobDetail?' + getJobParams)
      .reply(500)

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob', {
      params: userParams
    })

    response.status.should.equal(502)
  })
})

describe('GET /clusters/:clusterId/jobs/:jobId/status', () => {
  it('[P-01] should return job status', async () => {
    nock('http://universe')
      .get('/GetJobStatus?' + getJobStatusParams)
      .reply(200, {
        jobStatus: 'OK',
        errorMsg: null
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/status', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.have.property('status', 'OK')
  })

  it('[N-01] should return 502 Bad Gateway Error when the job does not exist', async () => {
    nock('http://universe')
      .get('/GetJobStatus?' + getJobStatusParams)
      .reply(500)

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/status', {
      params: userParams
    })

    response.status.should.equal(502)
  })

  it('[N-02] should return 404 Not Found when there is an error message', async () => {
    nock('http://universe')
      .get('/GetJobStatus?' + getJobStatusParams)
      .reply(200, {
        jobStatus: 'an error happened',
        errorMsg: 'Job Status Not Found'
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/status', {
      params: userParams
    })

    response.status.should.equal(404)
    response.data.should.equal('Job Status Not Found')
  })
})

describe('GET /clusters/:clusterId/jobs/:jobId/commands', () => {
  it('should return job commands', async () => {
    nock('http://universe')
      .get('/GetCommands?' + getJobParams)
      .reply(200, {
        commands: 'test job commands'
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/commands', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.have.property('commands', 'test job commands')
  })

  it('should return 502 Bad Gateway Error when the job does not exist', async () => {
    nock('http://universe')
      .get('/GetCommands?' + getJobParams)
      .reply(500)

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/commands', {
      params: userParams
    })

    response.status.should.equal(502)
  })
})

describe('GET /clusters/:clusterId/jobs/:jobId/endpoints', () => {
  it('should return job endpoints', async () => {
    nock('http://universe')
      .get('/endpoints?' + getJobParams)
      .reply(200, {
        endpoints: 'test job endpoints'
      })

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/endpoints', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.have.property('endpoints', 'test job endpoints')
  })

  it('should return 502 Bad Gateway Error when the job does not exist', async () => {
    nock('http://universe')
      .get('/endpoints?' + getJobParams)
      .reply(500)

    const response = await axiosist(api).get('/clusters/Universe/jobs/testjob/endpoints', {
      params: userParams
    })

    response.status.should.equal(502)
  })
})
