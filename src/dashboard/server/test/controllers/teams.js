const axiosist = require('axiosist')
const config = require('config')
const nock = require('nock')
const api = require('../../api').callback()
const User = require('../../api/services/user')

const clusterConfig = config.get('clusters')

// team data for the positive case
const posTeamData = Object.create(null)

posTeamData['Universe'] = {
  result: [{
    vcName: 'Universe',
    admin: 'AdminUniverse',
    metadata: '{"testmodel": {"num_gpu_per_node": "5"}, "user_quota": "3"}',
    quota: '{"testmodel": "2"}'
  }]
}

posTeamData['Targaryen'] = {
  result: [{
    vcName: 'Targaryen',
    admin: 'AdminTargaryen',
    metadata: '{"testmodel": {"num_gpu_per_node": "3"}, "user_quota": "1"}',
    quota: '{"nottestmodel": "0"}'
  }]
}

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

const fetchParams = new URLSearchParams({
  userName: 'dlts@example.com'
})

describe('GET /teams', function () {
  it('[P-01] should return the teams info of cluster', async function () {
    for (const key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListVCs?' + fetchParams)
        .reply(200, posTeamData[key])
    }

    const response = await axiosist(api).get('/teams', {
      params: userParams
    })

    response.data[0].should.have.property('id', 'Universe')
    response.data[0].clusters[0].gpus.should.ownProperty('testmodel')
    response.data[1].should.have.property('id', 'Targaryen')
    response.data[1].clusters[0].gpus.should.ownProperty('testmodel')
  })

  it('[N-01] should return empty gpus info with incorrect metadata or quota format', async function () {
    for (const key in clusterConfig) {
      // team data for the wrong format negative case
      const negTeamData = {
        result: [{
          vcName: key,
          admin: `Admin${key}`,
          metadata: 'wrong format',
          quota: 'wrong format'
        }]
      }

      nock(clusterConfig[key]['restfulapi'])
        .get('/ListVCs?' + fetchParams)
        .reply(200, negTeamData)
    }

    const response = await axiosist(api).get('/teams', {
      params: userParams
    })

    response.data[0].should.have.property('id', 'Universe')
    response.data[0].clusters[0].gpus.should.be.empty()
    response.data[1].should.have.property('id', 'Targaryen')
    response.data[1].clusters[0].gpus.should.be.empty()
  })

  it('[N-02] response data should be empty when there is a server error', async function () {
    for (const key in clusterConfig) {
      // team data for the empty data case
      const negTeamData = {
        result: {}
      }

      nock(clusterConfig[key]['restfulapi'])
        .get('/ListVCs?' + fetchParams)
        .reply(500, negTeamData)
    }

    const response = await axiosist(api).get('/teams', {
      params: userParams
    })

    response.data.should.be.empty()
  })
})
