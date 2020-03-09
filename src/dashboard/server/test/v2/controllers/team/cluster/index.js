const axiosist = require('axiosist')
const nock = require('nock')
const api = require('../../../../../api').callback()
const User = require('../../../../../api/services/user')

const EMAIL = 'dlts@example.com'
const PASSWORD = User.generateToken(EMAIL).toString('hex')
const TEAM_ID = 'theTeam'

describe('GET /teams/:teamId/clusters/:clusterId', () => {
  it('should return cluster status', async () => {
    nock('http://Universe')
      .get('/GetVC?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }))
      .reply(200, {
        AvaliableJobNum: 0
      })

    const response = await axiosist(api).get(`/v2/teams/${TEAM_ID}/clusters/Universe`, {
      params: {
        email: EMAIL,
        password: PASSWORD
      }
    })

    response.status.should.equal(200)
    response.data.should.have.property('config')
    response.data.config.should.have.property('grafana', 'http://grafana.universe')

    response.data.should.have.property('runningJobs', 0)

    // TODO: Add more field validation
  })
})
