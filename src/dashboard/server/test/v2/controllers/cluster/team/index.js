const axiosist = require('axiosist')
const nock = require('nock')
const api = require('../../../../../api').callback()
const User = require('../../../../../api/services/user')

const USER_NAME = 'dlts'
const EMAIL = `${USER_NAME}@example.com`
const PASSWORD = User.generateToken(EMAIL).toString('hex')
const TEAM_ID = 'theTeam'
const TYPE_NAME = 'standard'
const WORKER_NAME = 'worker'
const WORKER_1_NAME = 'worker-1'
const POD_NAME = 'pod'
const JOB_ID = 'job'

describe('GET /clusters/:clusterId/teams/:teamId', function () {
  it('should return cluster status', async function () {
    nock('http://Universe')
      .get('/GetVC?' + new URLSearchParams({ userName: EMAIL, vcName: TEAM_ID }))
      .reply(200, {
        AvaliableJobNum: 0,

        cpu_capacity: { [TYPE_NAME]: 1 },
        cpu_unschedulable: { [TYPE_NAME]: 2 },
        cpu_used: { [TYPE_NAME]: 3 },
        cpu_preemptable_used: { [TYPE_NAME]: 4 },
        cpu_available: { [TYPE_NAME]: 5 },
        gpu_capacity: { [TYPE_NAME]: 6 },
        gpu_unschedulable: { [TYPE_NAME]: 7 },
        gpu_used: { [TYPE_NAME]: 8 },
        gpu_preemptable_used: { [TYPE_NAME]: 9 },
        gpu_available: { [TYPE_NAME]: 10 },
        memory_capacity: { [TYPE_NAME]: 11 },
        memory_unschedulable: { [TYPE_NAME]: 12 },
        memory_used: { [TYPE_NAME]: 13 },
        memory_preemptable_used: { [TYPE_NAME]: 14 },
        memory_available: { [TYPE_NAME]: 15 },

        user_status: [{
          userName: USER_NAME,
          userCPU: { [TYPE_NAME]: 16 },
          userGPU: { [TYPE_NAME]: 17 },
          userMemory: { [TYPE_NAME]: 18 }
        }],
        user_status_preemptable: [{
          userName: USER_NAME,
          userCPU: { [TYPE_NAME]: 19 },
          userGPU: { [TYPE_NAME]: 20 },
          userMemory: { [TYPE_NAME]: 21 }
        }],

        node_status: [{
          name: WORKER_NAME,
          labels: { worker: 'active' },
          unschedulable: false,
          InternalIP: '0.0.0.0',

          REPAIR_STATE: 'IN_SERVICE',
          REPAIR_MESSAGE: null,

          cpu_capacity: { [TYPE_NAME]: 24 },
          cpu_used: { [TYPE_NAME]: 25 },
          cpu_preemptable_used: { [TYPE_NAME]: 26 },
          cpu_allocatable: { [TYPE_NAME]: 27 },
          gpu_capacity: { [TYPE_NAME]: 28 },
          gpu_used: { [TYPE_NAME]: 29 },
          gpu_preemptable_used: { [TYPE_NAME]: 30 },
          gpu_allocatable: { [TYPE_NAME]: 31 },
          memory_capacity: { [TYPE_NAME]: 32 },
          memory_used: { [TYPE_NAME]: 33 },
          memory_preemptable_used: { [TYPE_NAME]: 34 },
          memory_allocatable: { [TYPE_NAME]: 35 }
        }, {
          name: WORKER_1_NAME,
          labels: { worker: 'active' },
          unschedulable: true,
          InternalIP: '0.0.0.0',

          REPAIR_STATE: 'OUT_OF_POOL',
          REPAIR_MESSAGE: 'out of pool!',

          cpu_capacity: { [TYPE_NAME]: 0 },
          cpu_used: { [TYPE_NAME]: 0 },
          cpu_preemptable_used: { [TYPE_NAME]: 0 },
          cpu_allocatable: { [TYPE_NAME]: 0 },
          gpu_capacity: { [TYPE_NAME]: 0 },
          gpu_used: { [TYPE_NAME]: 0 },
          gpu_preemptable_used: { [TYPE_NAME]: 0 },
          gpu_allocatable: { [TYPE_NAME]: 0 },
          memory_capacity: { [TYPE_NAME]: 0 },
          memory_used: { [TYPE_NAME]: 0 },
          memory_preemptable_used: { [TYPE_NAME]: 0 },
          memory_allocatable: { [TYPE_NAME]: 0 }
        }],

        pod_status: [{
          name: POD_NAME,
          node_name: WORKER_NAME,
          job_id: JOB_ID,
          vc_name: TEAM_ID,
          username: USER_NAME,
          cpu: { [TYPE_NAME]: 36 },
          gpu: { [TYPE_NAME]: 37 },
          memory: { [TYPE_NAME]: 38 }
        }]
      })

    const response = await axiosist(api).get(`/v2/clusters/Universe/teams/${TEAM_ID}`, {
      params: {
        email: EMAIL,
        password: PASSWORD
      }
    })

    response.status.should.equal(200)

    response.data.should.have.propertyByPath('config', 'grafana').equal('http://grafana.universe')

    response.data.should.have.property('runningJobs', 0)

    response.data.should.have.propertyByPath('types', TYPE_NAME, 'cpu', 'total').equal(1)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'cpu', 'unschedulable').equal(2)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'cpu', 'used').equal(3)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'cpu', 'preemptable').equal(4)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'cpu', 'available').equal(5)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'gpu', 'total').equal(6)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'gpu', 'unschedulable').equal(7)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'gpu', 'used').equal(8)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'gpu', 'preemptable').equal(9)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'gpu', 'available').equal(10)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'memory', 'total').equal(11)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'memory', 'unschedulable').equal(12)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'memory', 'used').equal(13)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'memory', 'preemptable').equal(14)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'memory', 'available').equal(15)

    response.data.should.have.propertyByPath('users', USER_NAME, 'types', TYPE_NAME, 'cpu', 'used').equal(16)
    response.data.should.have.propertyByPath('users', USER_NAME, 'types', TYPE_NAME, 'gpu', 'used').equal(17)
    response.data.should.have.propertyByPath('users', USER_NAME, 'types', TYPE_NAME, 'memory', 'used').equal(18)
    response.data.should.have.propertyByPath('users', USER_NAME, 'types', TYPE_NAME, 'cpu', 'preemptable').equal(19)
    response.data.should.have.propertyByPath('users', USER_NAME, 'types', TYPE_NAME, 'gpu', 'preemptable').equal(20)
    response.data.should.have.propertyByPath('users', USER_NAME, 'types', TYPE_NAME, 'memory', 'preemptable').equal(21)

    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'healthy').equal(true)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'ip').equal('0.0.0.0')
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'type').equal(TYPE_NAME)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'state').equal('IN_SERVICE')
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'message').be.null()
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'cpu', 'total').equal(24)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'cpu', 'used').equal(25)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'cpu', 'preemptable').equal(26)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'cpu', 'allocatable').equal(27)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'gpu', 'total').equal(28)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'gpu', 'used').equal(29)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'gpu', 'preemptable').equal(30)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'gpu', 'allocatable').equal(31)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'memory', 'total').equal(32)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'memory', 'used').equal(33)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'memory', 'preemptable').equal(34)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'status', 'memory', 'allocatable').equal(35)

    response.data.should.have.propertyByPath('workers', WORKER_1_NAME, 'state').equal('OUT_OF_POOL')
    response.data.should.have.propertyByPath('workers', WORKER_1_NAME, 'message').equal('out of pool!')

    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'pods', POD_NAME, 'jobId').equal(JOB_ID)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'pods', POD_NAME, 'team').equal(TEAM_ID)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'pods', POD_NAME, 'user').equal(USER_NAME)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'pods', POD_NAME, 'cpu').equal(36)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'pods', POD_NAME, 'gpu').equal(37)
    response.data.should.have.propertyByPath('workers', WORKER_NAME, 'pods', POD_NAME, 'memory').equal(38)

    response.data.should.have.propertyByPath('types', TYPE_NAME, 'node', 'total').equal(2)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'node', 'unschedulable').equal(1)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'node', 'used').equal(1)
    response.data.should.have.propertyByPath('types', TYPE_NAME, 'node', 'available').equal(1)
  })
})
