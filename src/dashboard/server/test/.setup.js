const nock = require('nock')

process.env.NODE_ENV = 'test'

beforeEach(() => {
  nock.cleanAll()
})

afterEach(() => {
  nock.pendingMocks().should.be.empty()
})
