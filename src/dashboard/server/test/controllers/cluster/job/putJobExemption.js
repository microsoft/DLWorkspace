const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const setNameParams = new URLSearchParams({
  jobId: 'd175',
  userName: userParams.email
})

describe('PUT /clusters/:clusterId/jobs/:jobId/exemption', function () {
  it('should return OK if exemption set successfully', async function () {
    nock('http://universe')
      .post('/GpuIdleKillExemption?' + setNameParams, { isExempted: true })
      .reply(200, {
        message: 'exemption set successfully'
      })

    const response = await axiosist(api).put('/clusters/Universe/jobs/d175/exemption',
      { isExempted: true }, { params: userParams })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'exemption set successfully')
  })

  it('should return 502 Bad Gateway error if name setting failed', async function () {
    nock('http://universe')
      .post('/GpuIdleKillExemption?' + setNameParams, { isExempted: true })
      .reply(500)

    const response = await axiosist(api).put('/clusters/Universe/jobs/d175/exemption',
      { isExempted: true }, { params: userParams })

    response.status.should.equal(502)
  })
})