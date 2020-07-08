const axiosist = require('axiosist')
const nock = require('nock')
const config = require('config')
const api = require('../../../api').callback()
const User = require('../../../api/services/user')

const clusterConfig = config.get('clusters')

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex'),
  teamId: 'testteam'
}

const getJobsParams = new URLSearchParams({
  userName: userParams.email,
  vcName: userParams.teamId,
  jobOwner: 'all',
  num: 10
})

const testJobs = {
  donejob: {
    jobId: 'donejob',
    priority: 1,
    jobTime: 18874
  },
  queuedjob: {
    jobId: 'queuedjob',
    priority: 2,
    jobTime: 18875
  },
  runjob: {
    jobId: 'runjob',
    priority: 3,
    jobTime: null
  },
  visjob: {
    jobId: 'visjob',
    priority: 4,
    jobTime: null
  }
}

describe('GET /teams/:teamId/jobs', function () {
  it('[P-01] should return jobs info in the team with user as all', async function () {
    for (const key in clusterConfig) {
      // nock for getJobs()
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListJobs?' + getJobsParams)
        .reply(200, {
          finishedJobs: testJobs['donejob'],
          queuedJobs: testJobs['queuedjob'],
          runningJobs: testJobs['runjob'],
          visualizationJobs: testJobs['visjob']
        })
      // nock for getJobPriority()
      nock(clusterConfig[key]['restfulapi'])
        .get('/jobs/priorities')
        .reply(200, {
          donejob: 0,
          queuedjob: 1,
          runjob: 2
        })
    }

    const response = await axiosist(api).get('/teams/testteam/jobs?user=all',
      { params: userParams })

    response.status.should.equal(200)
    response.data.length.should.equal(8)
  })

  it('[P-02] should return jobs info in the team with specific user', async function () {
    for (const key in clusterConfig) {
      // change the jobOwner in getJobs params
      getJobsParams.set('jobOwner', userParams.email)

      // nock for getJobs()
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListJobs?' + getJobsParams)
        .reply(200, {
          finishedJobs: testJobs['donejob'],
          queuedJobs: testJobs['queuedjob'],
          runningJobs: testJobs['runjob'],
          visualizationJobs: testJobs['visjob']
        })
      // nock for getJobPriority()
      nock(clusterConfig[key]['restfulapi'])
        .get('/jobs/priorities')
        .reply(200, {
          donejob: 0,
          queuedjob: 1,
          runjob: 2
        })
    }

    const response = await axiosist(api).get('/teams/testteam/jobs',
      { params: userParams })

    response.status.should.equal(200)
    response.data.length.should.equal(8)
  })

  it('[N-01] should return empty data if getJobs failed', async function () {
    // change back the jobOwner in getJobs params
    getJobsParams.set('jobOwner', 'all')

    for (const key in clusterConfig) {
      // nock for getJobs()
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListJobs?' + getJobsParams)
        .reply(500)
      // nock for getJobPriority()
      nock(clusterConfig[key]['restfulapi'])
        .get('/jobs/priorities')
        .reply(200, {
          donejob: 0,
          queuedjob: 1,
          runjob: 2
        })
    }

    const response = await axiosist(api).get('/teams/testteam/jobs?user=all',
      { params: userParams })

    response.status.should.equal(200)
    response.data.should.be.empty()
  })

  it('[N-02] should ignore errors if getJobsPriority failed', async function () {
    for (const key in clusterConfig) {
      // nock for getJobs()
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListJobs?' + getJobsParams)
        .reply(200, {
          finishedJobs: testJobs['donejob'],
          queuedJobs: testJobs['queuedjob'],
          runningJobs: testJobs['runjob'],
          visualizationJobs: testJobs['visjob']
        })
      // nock for getJobPriority()
      nock(clusterConfig[key]['restfulapi'])
        .get('/jobs/priorities')
        .reply(500)
    }

    const response = await axiosist(api).get('/teams/testteam/jobs?user=all',
      { params: userParams })

    response.status.should.equal(200)
    response.data.length.should.equal(8)
  })
})
