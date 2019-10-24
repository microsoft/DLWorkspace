const axiosist = require('axiosist')
const sinon = require('sinon')
const nock = require('nock')
const config = require('config')
const api = require('../../../api').callback()
const User = require('../../../api/services/user')

const clusterConfig = config.get('clusters')

const userParams = {
  email: 'dlts@example.com',
  token: User.generateToken('dlts@example.com').toString('hex'),
  teamId: 'testteam',
  templateName: 'newtemplate'
}

const updateTemplateParams = new URLSearchParams({
  userName: userParams.email,
  vcName: userParams.teamId,
  database: 'user',
  templateName: userParams.templateName
})

describe('PUT /teams/:teamId/templates/:templateName', () => {
  it('should return 204 if template updated successfully', async () => {
    for(let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .post('/templates?' + updateTemplateParams)
        .reply(200, {
          message: 'template updated successfully'
        })
    }
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api)
      .put('/teams/testteam/templates/newtemplate', null, {
        params: userParams
      })

    response.status.should.equal(204)
  })

  it('should return 502 if template updating failed', async () => {
    for(let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .post('/templates?' + updateTemplateParams)
        .reply(500)
    }
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api)
      .put('/teams/testteam/templates/newtemplate', null, {
        params: userParams
      })

    response.status.should.equal(502)
  })
})
