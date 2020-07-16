const axiosist = require('axiosist')
const nock = require('nock')
const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const scaleJobParams = new URLSearchParams({
  jobId: 'testjob',
  userName: userParams.email,
  mingpu: 0,
  maxgpu: 10
})

describe('/clusters/:clusterId/jobs/:jobId', function () {
  describe('POST /clusters/:clusterId/jobs/:jobId/gpus', function () {
    it('should return 200 when scaled successfully', async function () {
      nock('http://universe')
        .post('/ScaleJob?' + scaleJobParams)
        .reply(200, JSON.stringify('Successful'))

      const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/gpus',
        { min: 0, max: 10 }, { params: userParams })

      response.status.should.equal(200)
      response.data.should.equal('Successful')
    })

    it('should return 403 Forbidden Error if scaled failed', async function () {
      nock('http://universe')
        .post('/ScaleJob?' + scaleJobParams)
        .reply(403, JSON.stringify('Failed'))

      const response = await axiosist(api).post('/clusters/Universe/jobs/testjob/gpus',
        { min: 0, max: 10 }, { params: userParams })

      response.status.should.equal(403)
      response.data.should.equal('Failed')
    })
  })
})
