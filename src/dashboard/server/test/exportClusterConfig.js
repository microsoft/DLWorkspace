const config = require('config')
const axiosist = require('axiosist')
const sinon = require('sinon')
const { createHash } = require('crypto')
const User = require('../api/services/user')
const api = require('../api').callback()

const masterToken = config.get('masterToken')

function generateUserToken(email) {
  const hash = createHash('md5')
  hash.update(`${email}:${masterToken}`)
  return hash.digest('hex')
}

describe('GET /clusters/:clusterId', () => {
  it('should response cluster config', async () => {
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/Universe', {
      params: {
        email: 'dlts@example.com',
        token: generateUserToken(testEmail)
      }
    })
    response.data.should.have.property('restfulapi', 'http://universe')
  })

  it('should response 404 when cluster not exist', async () => {
    sinon.stub(User.prototype, 'fillIdFromWinbind').resolves();

    const response = await axiosist(api).get('/clusters/NewCluster', {
      params: {
        email: 'dlts@example.com',
        token: generateUserToken(testEmail)
      }
    })
    response.status.should.equal(404)
  })
})
