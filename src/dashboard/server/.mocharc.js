const { resolve } = require('path')

module.exports = {
  require: [
    'should'
  ],
  spec: [
    resolve(__dirname, 'test/.setup.js'),
    resolve(__dirname, 'test/**/*.js')
  ]
}
