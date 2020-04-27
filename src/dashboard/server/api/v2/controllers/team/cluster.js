const _ = require('lodash')

/**
 * @typedef {Object} State
 * @property {import('../../../services/cluster')} cluster
 */

/** @type {import('koa').Middleware<State>} */
module.exports = async context => {
  const { cluster } = context.state
  const { teamId } = context.params

  const team = await cluster.getTeam(teamId)
  const body = context.body = Object.create(null)

  const _team = _.chain(team)
  const _setBody = _.partial(_.set, body)

  _setBody('config', cluster.config)
  _setBody('runningJobs', _team.get('AvaliableJobNum'))

  for (const [type, number] of _team.get('cpu_capacity').entries()) {
    _setBody(['types', type, 'cpu', 'total'], number)
  }
  for (const [type, number] of _team.get('cpu_unschedulable').entries()) {
    _setBody(['types', type, 'cpu', 'unschedulable'], number)
  }
  for (const [type, number] of _team.get('cpu_used').entries()) {
    _setBody(['types', type, 'cpu', 'used'], number)
  }
  for (const [type, number] of _team.get('cpu_preemptable_used').entries()) {
    _setBody(['types', type, 'cpu', 'preemptable'], number)
  }
  for (const [type, number] of _team.get('cpu_available').entries()) {
    _setBody(['types', type, 'cpu', 'available'], number)
  }

  for (const [type, number] of _team.get('gpu_capacity').entries()) {
    _setBody(['types', type, 'gpu', 'total'], number)
  }
  for (const [type, number] of _team.get('gpu_unschedulable').entries()) {
    _setBody(['types', type, 'gpu', 'unschedulable'], number)
  }
  for (const [type, number] of _team.get('gpu_used').entries()) {
    _setBody(['types', type, 'gpu', 'used'], number)
  }
  for (const [type, number] of _team.get('gpu_preemptable_used').entries()) {
    _setBody(['types', type, 'gpu', 'preemptable'], number)
  }
  for (const [type, number] of _team.get('gpu_available').entries()) {
    _setBody(['types', type, 'gpu', 'available'], number)
  }

  for (const [type, number] of _team.get('memory_capacity').entries()) {
    _setBody(['types', type, 'memory', 'total'], number)
  }
  for (const [type, number] of _team.get('memory_unschedulable').entries()) {
    _setBody(['types', type, 'memory', 'unschedulable'], number)
  }
  for (const [type, number] of _team.get('memory_used').entries()) {
    _setBody(['types', type, 'memory', 'used'], number)
  }
  for (const [type, number] of _team.get('memory_preemptable_used').entries()) {
    _setBody(['types', type, 'memory', 'preemptable'], number)
  }
  for (const [type, number] of _team.get('memory_available').entries()) {
    _setBody(['types', type, 'memory', 'available'], number)
  }

  for (const user of _team.get('user_status').filter('userName')) {
    const userName = user['userName']
    for (const [type, number] of _.chain(user).get('userCPU').entries()) {
      _setBody(['users', userName, 'types', type, 'cpu', 'used'], number)
    }
    for (const [type, number] of _.chain(user).get('userGPU').entries()) {
      _setBody(['users', userName, 'types', type, 'gpu', 'used'], number)
    }
    for (const [type, number] of _.chain(user).get('userMemory').entries()) {
      _setBody(['users', userName, 'types', type, 'memory', 'used'], number)
    }
  }
  for (const user of _team.get('user_status_preemptable').filter('userName')) {
    const _user = _.chain(user)
    const userName = user['userName']
    for (const [type, number] of _user.get('userCPU').entries()) {
      _setBody(['users', userName, 'types', type, 'cpu', 'preemptable'], number)
    }
    for (const [type, number] of _user.get('userGPU').entries()) {
      _setBody(['users', userName, 'types', type, 'gpu', 'preemptable'], number)
    }
    for (const [type, number] of _user.get('userMemory').entries()) {
      _setBody(['users', userName, 'types', type, 'memory', 'preemptable'], number)
    }
  }

  for (const [userName, data] of _team.get('gpu_idle').entries()) {
    _setBody(['users', userName, 'gpu', 'booked'], data['booked'])
    _setBody(['users', userName, 'gpu', 'idle'], data['idle'])
  }

  for (const node of _team.get('node_status').filter(_.matches({ 'labels': { 'worker': 'active' } }))) {
    const _node = _.chain(node)
    _setBody(['workers', node.name, 'healthy'], !node['unschedulable'])
    _setBody(['workers', node.name, 'ip'], node['InternalIP'])
    for (const [type, number] of _node.get('cpu_capacity').entries()) {
      _setBody(['workers', node.name, 'type'], type)
      _setBody(['workers', node.name, 'status', 'cpu', 'total'], number)
    }
    for (const number of _node.get('cpu_used').values()) {
      _setBody(['workers', node.name, 'status', 'cpu', 'used'], number)
    }
    for (const number of _node.get('cpu_preemptable_used').values()) {
      _setBody(['workers', node.name, 'status', 'cpu', 'preemptable'], number)
    }
    for (const number of _node.get('cpu_allocatable').values()) {
      _setBody(['workers', node.name, 'status', 'cpu', 'allocatable'], number)
    }
    for (const number of _node.get('gpu_capacity').values()) {
      _setBody(['workers', node.name, 'status', 'gpu', 'total'], number)
    }
    for (const number of _node.get('gpu_used').values()) {
      _setBody(['workers', node.name, 'status', 'gpu', 'used'], number)
    }
    for (const number of _node.get('gpu_preemptable_used').values()) {
      _setBody(['workers', node.name, 'status', 'gpu', 'preemptable'], number)
    }
    for (const number of _node.get('gpu_allocatable').values()) {
      _setBody(['workers', node.name, 'status', 'gpu', 'allocatable'], number)
    }
    for (const number of _node.get('memory_capacity').values()) {
      _setBody(['workers', node.name, 'status', 'memory', 'total'], number)
    }
    for (const number of _node.get('memory_used').values()) {
      _setBody(['workers', node.name, 'status', 'memory', 'used'], number)
    }
    for (const number of _node.get('memory_preemptable_used').values()) {
      _setBody(['workers', node.name, 'status', 'memory', 'preemptable'], number)
    }
    for (const number of _node.get('memory_allocatable').values()) {
      _setBody(['workers', node.name, 'status', 'memory', 'allocatable'], number)
    }
  }

  for (const pod of _team.get('pod_status')) {
    const _pod = _.chain(pod)

    const nodeName = _pod.get('node_name')
    const podName = _pod.get('name')
    _setBody(['workers', nodeName, 'pods', podName, 'jobId'], _pod.get('job_id'))
    _setBody(['workers', nodeName, 'pods', podName, 'team'], _pod.get('vc_name'))
    _setBody(['workers', nodeName, 'pods', podName, 'user'], _pod.get('username'))
    for (const number of _pod.get('cpu').values()) {
      _setBody(['workers', nodeName, 'pods', podName, 'cpu'], number)
    }
    for (const number of _pod.get('gpu').values()) {
      _setBody(['workers', nodeName, 'pods', podName, 'gpu'], number)
    }
    for (const number of _pod.get('memory').values()) {
      _setBody(['workers', nodeName, 'pods', podName, 'memory'], number)
    }
  }
}
