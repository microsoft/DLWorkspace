const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const setNameParams = new URLSearchParams({
  userName: userParams.email,
  jobId: 'd175'
})

describe('PUT /clusters/:clusterId/jobs/:jobId/name', function () {
  it('should return OK if name set successfully', async function () {
    nock('http://universe')
      .post('/JobName?' + setNameParams, { name: 'dlts' })
      .reply(200, {
        message: 'name set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/d175/name',
      { name: 'dlts' }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'name set successfully')
  })

  it('should return 502 Bad Gateway error if name setting failed', async function () {
    nock('http://universe')
      .post('/JobName?' + setNameParams, { name: 'dlts' })
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/d175/name',
      { name: 'dlts' }, { params: userParams })

    response.status.should.equal(502)
  })
})
