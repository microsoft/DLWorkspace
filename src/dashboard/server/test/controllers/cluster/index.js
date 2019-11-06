const axiosist = require('axiosist')
const sinon = require('sinon')
const User = require('../../../api/services/user')
const api = require('../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  token: User.generateToken('dlts@example.com').toString('hex')
}

describe('GET /clusters/:clusterId', () => {
  it('should response cluster config', async () => {
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/Universe', {
      params: userParams
    })
    response.data.should.have.property('restfulapi', 'http://universe')
  })

  it('should response 404 when cluster not exist', async () => {
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/NewCluster', {
      params: userParams
    })
    response.status.should.equal(404)
  })
})
