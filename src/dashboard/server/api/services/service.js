/**
 * @typedef {Object} State
 * @property {import('./user')} user
 */

/**
 * @abstract
 */
class Service {
  /**
   * @param {import('koa').ParameterizedContext<State>} context
   */
  constructor (context) {
    this.context = context
    Object.defineProperty(this, 'context', {
      enumerable: false,
      writable: false
    })
  }
}

module.exports = Service
