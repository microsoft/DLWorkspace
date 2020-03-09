const axiosist = require('axiosist')
const nock = require('nock')
const api = require('../../../api').callback()
const User = require('../../../api/services/user')

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex'),
  teamId: 'testteam'
}

const getTeamParams = new URLSearchParams({
  userName: userParams.email,
  vcName: userParams.teamId
})

describe('GET /teams/:teamId/clusters/:clusterId', function () {
  it('[P-01] should return team info', async function () {
    nock('http://Universe')
      .get('/GetVC?' + getTeamParams)
      .reply(200, {
        message: 'test team info'
      })

    const response = await axiosist(api).get('/teams/testteam/clusters/Universe', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data.should.have.property('message', 'test team info')
  })

  it('[N-01] should return 502 Bad Gateway error if team info getting failed', async function () {
    nock('http://Universe')
      .get('/GetVC?' + getTeamParams)
      .reply(500)

    const response = await axiosist(api).get('/teams/testteam/clusters/Universe', {
      params: userParams
    })

    response.status.should.equal(502)
  })

  it('[N-02] should return 404 Team is not found if returned team info is empty', async function () {
    nock('http://Universe')
      .get('/GetVC?' + getTeamParams)
      .reply(200, null)

    const response = await axiosist(api).get('/teams/testteam/clusters/Universe', {
      params: userParams
    })

    response.status.should.equal(404)
    response.data.should.equal('Team is not found')
  })
})
