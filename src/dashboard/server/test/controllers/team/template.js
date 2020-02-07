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

const getTemplatesParams = new URLSearchParams({
  userName: userParams.email,
  vcName: userParams.teamId
})

describe('GET /teams/:teamId/templates', () => {
  it('should return template info', async () => {
    for (let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .get('/templates?' + getTemplatesParams)
        .reply(200, {
          name: key
        })
    }

    const response = await axiosist(api).get('/teams/testteam/templates', {
      params: userParams
    })

    response.status.should.equal(200)
    response.data[0].should.have.property('name', 'Universe')
    response.data[1].should.have.property('name', 'Targaryen')
  })

  it('response should be empty if templates getting failed', async () => {
    for (let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .get('/templates?' + getTemplatesParams)
        .reply(500)
    }

    const response = await axiosist(api).get('/teams/testteam/templates', {
      params: userParams
    })

    response.data.should.be.empty()
  })
})
