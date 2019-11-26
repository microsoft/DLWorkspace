const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const setPriorityParams = new URLSearchParams({
  userName: userParams.email
})

describe('PUT /clusters/:clusterId/jobs/:jobId/priority', () => {
  it('should return OK if priority set successfully', async () => {
    nock('http://universe')
      .post('/jobs/priorities?' + setPriorityParams, { 'testjob': /[0-9]+/ })
      .reply(200, {
        message: 'priority set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/priority',
      { priority: 0 }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'priority set successfully')
  })

  it('should return 502 Bad Gateway error if priority setting failed', async () => {
    nock('http://universe')
      .post('/jobs/priorities?' + setPriorityParams, { 'testjob': /[0-9]+/ })
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/testjob/priority',
      { priority: 0 }, { params: userParams })

    response.status.should.equal(502)
  })
})
