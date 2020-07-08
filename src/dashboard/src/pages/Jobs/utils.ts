import { groupBy } from 'lodash'

export type Job = any

const ACTIVE_STATUSES: { [status: string]: string } = {
  unapproved: 'Unapproved',
  queued: 'Pending',
  scheduling: 'Pending',
  running: 'Running',
  pausing: 'Paused',
  paused: 'Paused'
}

export const groupByActiveStatus = (jobs: Array<Job>) => {
  return groupBy(jobs, (job) => {
    return ACTIVE_STATUSES[job['jobStatus']] || 'Inactive'
  })
}
