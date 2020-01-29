const { resolve } = require('path')

module.exports = {
  cwd: __dirname,
  includes: [
    resolve(__dirname, 'api/**/*.js')
  ]
}
