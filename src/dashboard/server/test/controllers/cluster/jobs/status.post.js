const axiosist = require('axiosist')
const nock = require('nock')

const User = require('../../../../api/services/user')
const api = require('../../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

describe('POST /clusters/:clusterid/jobs/status', function () {
  it('should response successful message of each type of status', async function () {
    nock('http://universe')
      .get('/ApproveJobs')
      .query({ jobIds: 'approve1,approve2', userName: userParams.email })
      .reply(200, 'approve succeeded')
    nock('http://universe')
      .get('/PauseJobs')
      .query({ jobIds: 'pause1,pause2', userName: userParams.email })
      .reply(200, 'pause succeeded')
    nock('http://universe')
      .get('/ResumeJobs')
      .query({ jobIds: 'resume1,resume2', userName: userParams.email })
      .reply(200, 'resume succeeded')
    nock('http://universe')
      .get('/KillJobs')
      .query({ jobIds: 'kill1,kill2', userName: userParams.email })
      .reply(200, 'kill succeeded')

    const response = await axiosist(api).post('/clusters/Universe/jobs/status', {
      status: {
        approve1: 'approved',
        approve2: 'approved',
        pause1: 'pausing',
        pause2: 'pausing',
        resume1: 'queued',
        resume2: 'queued',
        kill1: 'killing',
        kill2: 'killing'
      }
    }, { params: userParams })

    response.status.should.equal(200)
    Object.keys(response.data).length.should.be.equal(4)
    response.data.should.have.property('approved', 'approve succeeded')
    response.data.should.have.property('pausing', 'pause succeeded')
    response.data.should.have.property('queued', 'resume succeeded')
    response.data.should.have.property('killing', 'kill succeeded')
  })
})
