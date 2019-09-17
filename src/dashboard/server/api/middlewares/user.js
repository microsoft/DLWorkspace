const User = require('../services/user')

/**
 * @param {boolean} force
 * @return {import('koa').Middleware}
 */
module.exports = (forceAuthenticated = true) => async (context, next) => {
  if ('email' in context.query && 'token' in context.query) {
    const { email, token } = context.query
    const user = context.state.user = User.fromToken(context, email, token)
    await user.fillIdFromWinbind()
    context.log.info(user, 'Authenticated by token')
  } else if (context.cookies.get('token')) {
    try {
      const token = context.cookies.get('token')
      const user = context.state.user = User.fromCookie(context, token)
      await user.token
      context.log.info(user, 'Authenticated by cookie')
    } catch (error) {
      context.log.error(error, 'Error in cookie authentication')
    }
  }

  if (forceAuthenticated) {
    context.assert(context.state.user != null, 403)
  }

  return next()
}
