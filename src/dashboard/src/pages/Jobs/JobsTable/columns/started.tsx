import { Column } from 'material-table'
import { get } from 'lodash'

import { Job } from '../../utils'

import renderDate from './utils/renderDate'

const CACHE_KEY = '__DLTS_STARTED'

const valueOf = (job: Job): Date => {
  if (CACHE_KEY in job) return job[CACHE_KEY]

  const date = new Date(get(job, 'jobStatusDetail.0.startedAt'))
  return job[CACHE_KEY] = date
}

export default (): Column<Job> => ({
  title: 'Started',
  type: 'datetime',
  render (job) {
    return renderDate(valueOf(job))
  },
  customSort (job1, job2) {
    return valueOf(job1).getTime() - valueOf(job2).getTime()
  }
})
