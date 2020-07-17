const axiosist = require('axiosist')
const nock = require('nock')
const api = require('../../api').callback()
const User = require('../../api/services/user')

const userParams = {
  email: 'dlts@example.com',
  password: User.generateToken('dlts@example.com').toString('hex')
}

describe('/keys', function () {
  describe('GET /keys', function () {
    it('should return key list', async function () {
      nock('http://ether')
        .get('/PublicKey?' + new URLSearchParams({ username: 'dlts@example.com' }))
        .reply(200, [{
          'key_title': 'title',
          'public_key': 'key',
          'add_time': '2000-01-01T00:00:00',
          'id': 1
        }])

      const response = await axiosist(api).get('/keys', {
        params: userParams
      })

      response.status.should.equal(200)
      response.data.should.be.Array().and.have.length(1)
      response.data[0].should.have.property('id', 1)
      response.data[0].should.have.property('name', 'title')
      response.data[0].should.have.property('key', 'key')
      response.data[0].should.have.property('added', '2000-01-01T00:00:00')
    })
  })

  describe('POST /keys', function () {
    it('should add key', async function () {
      nock('http://ether')
        .post('/PublicKey?' + new URLSearchParams({
          username: 'dlts@example.com',
          key_title: 'title'
        }), {
          'public_key': 'key'
        })
        .reply(200, { 'id': 1 })

      const response = await axiosist(api).post('/keys', {
        name: 'title',
        key: 'key'
      }, {
        params: userParams
      })

      response.status.should.equal(201)
      response.headers.should.have.property('location', '/keys/1')
    })
  })

  describe('DELETE /key/:keyId', function () {
    it('should delete key', async function () {
      nock('http://ether')
        .delete('/PublicKey?' + new URLSearchParams({
          username: 'dlts@example.com',
          key_id: 1
        }))
        .reply(200)

      const response = await axiosist(api).delete('/keys/1', {
        params: userParams
      })

      response.status.should.equal(200)
    })

    it('should return 404 if key not exists', async function () {
      nock('http://ether')
        .delete('/PublicKey?' + new URLSearchParams({
          username: 'dlts@example.com',
          key_id: 1
        }))
        .reply(404)

      const response = await axiosist(api).delete('/keys/1', {
        params: userParams
      })

      response.status.should.equal(404)
    })
  })
})
