const config = require('config')

const activeDirectoryConfig = config.get('activeDirectory')

const OAUTH2_URL = `https://login.microsoftonline.com/${activeDirectoryConfig.tenant}/oauth2`

/** @type {import('koa').Middleware} */
module.exports = async context => {
  context.cookies.set('token')
  return context.redirect(OAUTH2_URL + '/logout')
}
