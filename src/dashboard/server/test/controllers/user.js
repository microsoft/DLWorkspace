const axiosist = require('axiosist')
const User = require('../../api/services/user')
const api = require('../../api').callback()

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

describe('GET /user', function () {
  it('should response user password', async function () {
    const response = await axiosist(api).get('/user', {
      params: userParams
    })
    response.data.should.have.property('password', `${userParams.password}`)
  })
})
