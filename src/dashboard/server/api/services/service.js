/**
 * @typedef {Object} State
 * @property {import('./user')} user
 */

/**
 * @abstract
 * @template State
 */
class Service {
  /**
   * @param {import('koa').ParameterizedContext<State>} context
   */
  constructor (context) {
    Object.defineProperty(this, 'context', { value: context })
  }
}

module.exports = Service
