const axiosist = require('axiosist')
const config = require('config')
const sinon = require('sinon')
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
    metadata: `{"testmodel": {"num_gpu_per_node": "5"}, "user_quota": "3"}`,
    quota: `{"testmodel": "2"}`
  }]
}

posTeamData['Targaryen'] = {
  result: [{
    vcName: 'Targaryen',
    admin: 'AdminTargaryen',
    metadata: `{"testmodel": {"num_gpu_per_node": "3"}, "user_quota": "1"}`,
    quota: `{"nottestmodel": "0"}`
  }]
}

// team data for the first wrong format negative case
const negTeamData1 = Object.create(null)

negTeamData1['Universe'] = {
  result: [{
    vcName: 'Universe',
    admin: 'AdminUniverse',
    metadata: 'wrong format',
    quota: 'wrong format'
  }]
}

negTeamData1['Targaryen'] = {
  result: [{
    vcName: 'Targaryen',
    admin: 'AdminTargaryen',
    metadata: 'wrong format',
    quota: 'wrong format'
  }]
}

// team data for the second empty team case
const negTeamData2 = Object.create(null)

negTeamData2['Universe'] = {result: {}}
negTeamData2['Targaryen'] = {result: {}}

const userParams = {
  email: 'dlts@example.com',
  token: User.generateToken('dlts@example.com').toString('hex')
}

const fetchParams = new URLSearchParams({
  userName: 'dlts@example.com'
})

describe('GET /teams', () => {
  it('[P-01]: should return the teams info of cluster', async () => {
    for(let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListVCs?' + fetchParams)
        .reply(200, posTeamData[key])
    }
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/teams', {
      params: userParams
    })

    response.data[0].should.have.property('id', 'Universe')
    response.data[0].clusters[0].gpus.should.ownProperty('testmodel')
    response.data[1].should.have.property('id', 'Targaryen')
    response.data[1].clusters[0].gpus.should.ownProperty('testmodel')
  })

  it('[N-01]: should return empty gpus info with incorrect metadata or quota format', async () => {
    for(let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListVCs?' + fetchParams)
        .reply(200, negTeamData1[key])
    }
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/teams', {
      params: userParams
    })

    response.data[0].should.have.property('id', 'Universe')
    response.data[0].clusters[0].gpus.should.be.empty()
    response.data[1].should.have.property('id', 'Targaryen')
    response.data[1].clusters[0].gpus.should.be.empty()
  })

  it('[N-02]: response data should be empty when there is a server error', async () => {
    for(let key in clusterConfig) {
      nock(clusterConfig[key]['restfulapi'])
        .get('/ListVCs?' + fetchParams)
        .reply(200, negTeamData2[key])
    }
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/teams', {
      params: userParams
    })

    response.data.should.be.empty()
  })
})
