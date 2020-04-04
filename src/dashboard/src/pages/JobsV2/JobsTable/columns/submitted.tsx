import { Column } from 'material-table';

import { Job } from '../../utils';

import renderDate from './utils/renderDate';

const CACHE_KEY = '__DLTS_SUBMITTED';

const valueOf = (job: Job): Date => {
  if (CACHE_KEY in job) return job[CACHE_KEY];

  const date = new Date(job['jobTime']);
  return job[CACHE_KEY] = date;
};

export default (): Column<Job> => ({
  title: 'Submitted',
  type: 'datetime',
  render(job) {
    return renderDate(valueOf(job));
  },
  customSort(job1, job2) {
    return valueOf(job1).getTime() - valueOf(job2).getTime();
  }
});
