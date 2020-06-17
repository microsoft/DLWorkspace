const axiosist = require('axiosist')
const nock = require('nock')
const api = require('../../../../../api').callback()
const User = require('../../../../../api/services/user')

const USER_NAME = 'dlts'
const EMAIL = `${USER_NAME}@example.com`
const PASSWORD = User.generateToken(EMAIL).toString('hex')
const JOB_ID = 'job'
const LOG = 'FirstLine\nSecondLine\n'

describe('GET /clusters/:clusterId/teams/:teamId', function () {
  it('should return cluster status', async function () {
    nock('http://Universe')
      .get('/GetJobRawLog?' + new URLSearchParams({ userName: EMAIL, jobId: JOB_ID }))
      .reply(200, LOG)

    const response = await axiosist(api).get(`/v2/clusters/Universe/jobs/${JOB_ID}/log`, {
      params: {
        email: EMAIL,
        password: PASSWORD
      }
    })
    response.data.should.be.equal(LOG)
  })
})
