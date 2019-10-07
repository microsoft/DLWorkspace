module.exports = (app) => {
  app.use('/api', require('../server/api').callback())
}
