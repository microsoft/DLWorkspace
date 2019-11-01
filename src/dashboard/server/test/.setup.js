const nock = require('nock')
const sinon = require('sinon')

process.env.NODE_ENV = 'test'

beforeEach(() => {
  nock.cleanAll()
  sinon.restore()
})

afterEach(() => {
  nock.pendingMocks().should.be.empty()
  sinon.verify()
})
