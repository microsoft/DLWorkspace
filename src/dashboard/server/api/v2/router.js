const Router = require('koa-router')

const router = module.exports = new Router({
  sensitive: true,
  strict: true
})

router.get('/', require('./controllers'))
router.get('/openapi.yaml', require('./controllers/openapi'))

router.param('clusterId',
  require('./middlewares/cluster'))

router.get('/clusters/:clusterId/teams/:teamId',
  require('../middlewares/user')(),
  require('./controllers/cluster/team'))
router.get('/clusters/:clusterId/teams/:teamId/meta',
  require('../middlewares/user')(),
  require('./controllers/cluster/team/meta'))
router.patch('/clusters/:clusterId/teams/:teamId/meta',
  require('../middlewares/user')(),
  require('../middlewares/body')('meta'),
  require('./controllers/cluster/team/meta.patch'))
router.get('/clusters/:clusterId/teams/:teamId/jobs',
  require('../middlewares/user')(),
  require('./controllers/cluster/team/jobs'))
router.get('/clusters/:clusterId/jobs/:jobId',
  require('../middlewares/user')(),
  require('./controllers/cluster/job'))
router.get('/clusters/:clusterId/jobs/:jobId/log',
  require('../middlewares/user')(),
  require('./controllers/cluster/job/log'))
