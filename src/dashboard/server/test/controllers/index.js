const axiosist = require('axiosist')

const api = require('../../api').callback()

describe('GET /', () => {
  it('should returns version of the API', async () => {
    const response = await axiosist(api).get('/')
    response.data.should.be.an.Object()
      .and.have.property('version')
  })
})
