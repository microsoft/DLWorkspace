const Router = require('koa-router')

const router = module.exports = new Router()

router.get('/', require('./controllers'))
router.get('/openapi.yaml', require('./controllers/openapi'))

router.param('clusterId',
  require('./middlewares/cluster'))

router.get('/clusters/:clusterId/teams/:teamId/jobs',
  require('../middlewares/user')(),
  require('./controllers/cluster/team/jobs'))
router.get('/clusters/:clusterId/jobs/:jobId',
  require('../middlewares/user')(),
  require('./controllers/cluster/job'))
