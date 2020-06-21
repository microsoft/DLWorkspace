const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  jobId: 'testjob',
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const addCommandParams = new URLSearchParams({
  jobId: 'testjob',
  userName: userParams.email,
  command: 'testcommand'
})

const addEndpointsParams = new URLSearchParams({
  userName: userParams.email
})

const testEndpoints = {
  endpoints: [{
    name: 'testname',
    podPort: 0
  }, {
    name: 'testname2',
    podPort: 1
  }]
}

describe('POST /clusters/:clusterId/jobs/:jobId/commands', function () {
  it('should return 201 when command is added successfully', async function () {
    nock('http://universe')
      .get('/AddCommand?' + addCommandParams)
      .reply(200, {
        message: 'command adding succeeded'
      })

    const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/commands',
      { command: 'testcommand' }, { params: userParams })

    response.status.should.equal(201)
    response.data.should.have.property('message', 'command adding succeeded')
  })

  it('should return 502 Bad Gateway Error if command adding failed', async function () {
    nock('http://universe')
      .get('/AddCommand?' + addCommandParams)
      .reply(500)

    const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/commands',
      { command: 'testcommand' }, { params: userParams })

    response.status.should.equal(502)
  })
})

describe('POST /clusters/:clusterId/jobs/:jobId/endpoints', function () {
  it('should return 200 when endpoints are added successfully', async function () {
    nock('http://universe')
      .post('/endpoints?' + addEndpointsParams)
      .reply(200, {
        message: 'endpoints adding succeeded'
      })

    const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/endpoints',
      testEndpoints, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'endpoints adding succeeded')
  })

  it('should return 403 with messages when endpoints are added failed with 403', async function () {
    nock('http://universe')
      .post('/endpoints?' + addEndpointsParams)
      .reply(403, 'endpoints adding failed')

    const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/endpoints',
      testEndpoints, { params: userParams })

    response.status.should.equal(403)
    response.data.should.equal('endpoints adding failed')
  })

  it('should return 502 Bad Gateway Error if endpoints adding failed', async function () {
    nock('http://universe')
      .post('/endpoints?' + addEndpointsParams)
      .reply(500)

    const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/endpoints',
      testEndpoints, { params: userParams })

    response.status.should.equal(502)
  })
})
