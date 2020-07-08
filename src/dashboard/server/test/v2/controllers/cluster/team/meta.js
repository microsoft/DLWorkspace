const axiosist = require('axiosist')
const nock = require('nock')
const api = require('../../../../../api').callback()
const User = require('../../../../../api/services/user')

const EMAIL = 'dlts@example.com'
const PASSWORD = User.generateToken(EMAIL).toString('hex')
const TEAM_ID = 'team'

describe('GET /clusters/:clusterId/teams/:teamId/meta', function () {
  it('should return team meta', async function () {
    nock('http://Universe')
      .get('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }))
      .reply(200, {
        'job_max_time_second': 100,
        'interactive_limit': 20,
        'scheduling_policy': 'RF'
      })

    const response = await axiosist(api).get(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
      params: {
        email: EMAIL,
        password: PASSWORD
      }
    })

    response.status.should.equal(200)
    response.data.should.have.property('timeout', 100)
    response.data.should.have.property('interactiveGpu', 20)
    response.data.should.have.property('schedulingPolicy', 'RF')
  })

  it('should be able to update team meta', async function () {
    nock('http://Universe')
      .post('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }), {
        'job_max_time_second': 100,
        'interactive_limit': 20,
        'scheduling_policy': 'RF'
      })
      .reply(204)

    const response = await axiosist(api).patch(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
      timeout: 100,
      interactiveGpu: 20,
      schedulingPolicy: 'RF'
    }, {
      params: {
        email: EMAIL,
        password: PASSWORD
      }
    })

    response.status.should.equal(204)
  })

  describe('should be able to update partial team meta', function () {
    it('timeout: number', async function () {
      nock('http://Universe')
        .post('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }), {
          'job_max_time_second': 100
        })
        .reply(204)

      const response = await axiosist(api).patch(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
        timeout: 100
      }, {
        params: {
          email: EMAIL,
          password: PASSWORD
        }
      })

      response.status.should.equal(204)
    })

    it('timeout: null', async function () {
      nock('http://Universe')
        .post('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }), {
          'job_max_time_second': null
        })
        .reply(204)

      const response = await axiosist(api).patch(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
        timeout: null
      }, {
        params: {
          email: EMAIL,
          password: PASSWORD
        }
      })

      response.status.should.equal(204)
    })

    it('interactiveGpu: number', async function () {
      nock('http://Universe')
        .post('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }), {
          'interactive_limit': 20
        })
        .reply(204)

      const response = await axiosist(api).patch(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
        interactiveGpu: 20
      }, {
        params: {
          email: EMAIL,
          password: PASSWORD
        }
      })

      response.status.should.equal(204)
    })

    it('interactiveGpu: null', async function () {
      nock('http://Universe')
        .post('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }), {
          'interactive_limit': null
        })
        .reply(204)

      const response = await axiosist(api).patch(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
        interactiveGpu: null
      }, {
        params: {
          email: EMAIL,
          password: PASSWORD
        }
      })

      response.status.should.equal(204)
    })

    it('schedulingPolicy: RF', async function () {
      nock('http://Universe')
        .post('/VCMeta?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }), {
          'scheduling_policy': 'RF'
        })
        .reply(204)

      const response = await axiosist(api).patch(`/v2/clusters/Universe/teams/${TEAM_ID}/meta`, {
        schedulingPolicy: 'RF'
      }, {
        params: {
          email: EMAIL,
          password: PASSWORD
        }
      })

      response.status.should.equal(204)
    })
  })
})
