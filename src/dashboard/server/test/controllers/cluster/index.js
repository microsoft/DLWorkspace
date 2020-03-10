const axiosist = require('axiosist')
const User = require('../../../api/services/user')
const api = require('../../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

describe('GET /clusters/:clusterId', function () {
  it('should response cluster config', async function () {
    const response = await axiosist(api).get('/clusters/Universe', {
      params: userParams
    })
    response.data.should.have.property('restfulapi', 'http://universe')
  })

  it('should response 404 when cluster not exist', async function () {
    const response = await axiosist(api).get('/clusters/NewCluster', {
      params: userParams
    })
    response.status.should.equal(404)
  })
})
