const Router = require('koa-router')

const router = module.exports = new Router()

router.get('/',
  require('./controllers'))

router.get('/bootstrap.js',
  require('./middlewares/user')(false),
  require('./controllers/bootstrap'))
router.get('/authenticate',
  require('./controllers/authenticate'))
router.get('/authenticate/logout',
  require('./controllers/authenticate/logout'))

router.param('clusterId',
  require('./middlewares/cluster'))

router.get('/teams',
  require('./middlewares/user')(),
  require('./controllers/teams'))
router.get('/teams/:teamId/clusters/:clusterId',
  require('./middlewares/user')(),
  require('./controllers/team/cluster'))
router.get('/clusters/:clusterId',
  require('./middlewares/user')(),
  require('./controllers/cluster'))
router.get('/teams/:teamId/clusters/:clusterId/metadata',
  require('./middlewares/user')(),
  require('./controllers/team/cluster/metadata'))

router.get('/teams/:teamId/jobs',
  require('./middlewares/user')(),
  require('./controllers/team/jobs'))
router.post('/clusters/:clusterId/jobs',
  require('./middlewares/user')(),
  require('./middlewares/body')('job'),
  require('./controllers/cluster/jobs.post'))
router.post('/clusters/:clusterId/jobs/status',
  require('./middlewares/user')(),
  require('./middlewares/body')('batch-status'),
  require('./controllers/cluster/jobs/status.post'))
router.get('/clusters/:clusterId/jobs/:jobId',
  require('./middlewares/user')(),
  require('./controllers/cluster/job'))
router.get('/clusters/:clusterId/jobs/:jobId/status',
  require('./middlewares/user')(),
  require('./controllers/cluster/job/status'))
router.put('/clusters/:clusterId/jobs/:jobId/status',
  require('./middlewares/user')(),
  require('./middlewares/body')('status'),
  require('./controllers/cluster/job/status.put'))
router.put('/clusters/:clusterId/jobs/:jobId/priority',
  require('./middlewares/user')(),
  require('./middlewares/body')('priority'),
  require('./controllers/cluster/job/priority.put'))
router.get('/clusters/:clusterId/jobs/:jobId/log',
  require('./middlewares/user')(),
  require('./controllers/cluster/job/log'))

router.get('/clusters/:clusterId/jobs/:jobId/commands',
  require('./middlewares/user')(),
  require('./controllers/cluster/job/commands'))
router.post('/clusters/:clusterId/jobs/:jobId/commands',
  require('./middlewares/user')(),
  require('./middlewares/body')('command'),
  require('./controllers/cluster/job/commands.post'))

router.get('/clusters/:clusterId/jobs/:jobId/endpoints',
  require('./middlewares/user')(),
  require('./controllers/cluster/job/endpoints'))
router.post('/clusters/:clusterId/jobs/:jobId/endpoints',
  require('./middlewares/user')(),
  require('./middlewares/body')('endpoints'),
  require('./controllers/cluster/job/endpoints.post'))

router.get('/user',
  require('./middlewares/user')(),
  require('./controllers/user'))

router.get('/teams/:teamId/templates',
  require('./middlewares/user')(),
  require('./controllers/team/templates'))
router.put('/teams/:teamId/templates/:templateName',
  require('./middlewares/user')(),
  require('./middlewares/body')('template'),
  require('./controllers/team/template.put'))
router.delete('/teams/:teamId/templates/:templateName',
  require('./middlewares/user')(),
  require('./controllers/team/template.delete'))

router.get('/error.gif',
  require('./controllers/error'))
