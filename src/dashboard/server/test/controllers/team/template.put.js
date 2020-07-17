const axiosist = require('axiosist')
const nock = require('nock')
const config = require('config')
const api = require('../../../api').callback()
const User = require('../../../api/services/user')

const clusterConfig = config.get('clusters')

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex'),
  teamId: 'testteam',
  templateName: 'newtemplate'
}

const updateTemplateParams = new URLSearchParams({
  userName: userParams.email,
  vcName: userParams.teamId,
  database: 'user',
  templateName: userParams.templateName
})

describe('PUT /teams/:teamId/templates/:templateName', function () {
  it('should return 204 if template updated successfully', async function () {
    for (const key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .post('/templates?' + updateTemplateParams)
        .reply(200, {
          message: 'template updated successfully'
        })
    }

    const response = await axiosist(api)
      .put('/teams/testteam/templates/newtemplate', null, {
        params: userParams
      })

    response.status.should.equal(204)
  })

  it('should return 502 if template updating failed', async function () {
    for (const key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .post('/templates?' + updateTemplateParams)
        .reply(500)
    }

    const response = await axiosist(api)
      .put('/teams/testteam/templates/newtemplate', null, {
        params: userParams
      })

    response.status.should.equal(502)
  })
})
