const User = require('../services/user')
/**
 * @param {boolean} force
 * @return {import('koa').Middleware}
 */
module.exports = (forceAuthenticated = true) => async (context, next) => {
  console.log({ forceAuthenticated })
  if ('email' in context.query) {
    let { email, password } = context.query

    // Backward compatibility
    if (password === undefined) { password = context.query.token }

    if (password) {
      const user = context.state.user = User.fromPassword(context, email, password)
      context.log.debug(user, 'Authenticated by password')
    }
  } else if (context.cookies.get('token')) {
    try {
      const cookieToken = context.cookies.get('token')
      const user = context.state.user = User.fromCookieToken(context, cookieToken)
      context.log.debug(user, 'Authenticated by cookie')
    } catch (error) {
      context.log.error(error, 'Error in cookie authentication')
    }
  }

  if (forceAuthenticated) {
    context.assert(context.state.user != null, 403)
  }

  return next()
}
