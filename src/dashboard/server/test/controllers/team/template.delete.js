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

const deleteTemplateParams = new URLSearchParams({
  userName: userParams.email,
  vcName: userParams.teamId,
  database: 'user',
  templateName: userParams.templateName
})

describe('DELETE /teams/:teamId/templates/:templateName', function () {
  it('should return 204 if template deleted successfully', async function () {
    for (const key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .delete('/templates?' + deleteTemplateParams)
        .reply(200, {
          message: 'template deleted successfully'
        })
    }

    const response = await axiosist(api).delete('/teams/testteam/templates/newtemplate', {
      params: userParams
    })

    response.status.should.equal(204)
  })

  it('should return 502 if template deleting failed', async function () {
    for (const key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .delete('/templates?' + deleteTemplateParams)
        .reply(500)
    }

    const response = await axiosist(api).delete('/teams/testteam/templates/newtemplate', {
      params: userParams
    })

    response.status.should.equal(502)
  })
})
