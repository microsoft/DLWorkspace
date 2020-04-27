const axiosist = require('axiosist')

const api = require('../../api').callback()

describe('GET /', function () {
  it('should returns version of the API', async function () {
    const response = await axiosist(api).get('/')
    response.data.should.be.an.Object()
      .and.have.property('version')
  })
})
