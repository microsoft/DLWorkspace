const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const setStatusParams = new URLSearchParams({
  jobId: 'testjob',
  userName: userParams.email
})

describe('PUT /clusters/:clusterId/jobs/:jobId/status', function () {
  it('[P-01] should return OK if status approved set successfully', async function () {
    nock('http://universe')
      .get('/ApproveJob?' + setStatusParams)
      .reply(200, {
        message: 'status approved set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'approved' }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'status approved set successfully')
  })

  it('[P-02] should return OK if status killing set successfully', async function () {
    nock('http://universe')
      .get('/KillJob?' + setStatusParams)
      .reply(200, {
        message: 'status killing set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'killing' }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'status killing set successfully')
  })

  it('[P-03] should return OK if status pausing set successfully', async function () {
    nock('http://universe')
      .get('/PauseJob?' + setStatusParams)
      .reply(200, {
        message: 'status pausing set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'pausing' }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'status pausing set successfully')
  })

  // resume job
  it('[P-04] should return OK if status queued set successfully', async function () {
    nock('http://universe')
      .get('/ResumeJob?' + setStatusParams)
      .reply(200, {
        message: 'status queued set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'queued' }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'status queued set successfully')
  })

  it('[N-01] should return response status if approved set failed', async function () {
    nock('http://universe')
      .get('/ApproveJob?' + setStatusParams)
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'approved' }, { params: userParams })

    response.status.should.equal(500)
  })

  it('[N-02] should return response status if killing set failed', async function () {
    nock('http://universe')
      .get('/KillJob?' + setStatusParams)
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'killing' }, { params: userParams })

    response.status.should.equal(500)
  })

  it('[N-03] should return response status if pausing set failed', async function () {
    nock('http://universe')
      .get('/PauseJob?' + setStatusParams)
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'pausing' }, { params: userParams })

    response.status.should.equal(500)
  })

  it('[N-04] should return response status if queued set failed', async function () {
    nock('http://universe')
      .get('/ResumeJob?' + setStatusParams)
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'queued' }, { params: userParams })

    response.status.should.equal(500)
  })

  it('[N-05] should return 400 Invalid status when status is invalid', async function () {
    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/status',
      { status: 'invalid' }, { params: userParams })

    response.status.should.equal(400)
  })
})
