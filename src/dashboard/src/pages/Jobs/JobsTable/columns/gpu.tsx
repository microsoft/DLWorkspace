import * as React from 'react';
import { Column } from 'material-table';
import { get } from 'lodash';

import { Job } from '../../utils';

const CACHE_KEY = '__DLTS_GPU';

const valueOf = (job: Job): number => {
  if (CACHE_KEY in job) return job[CACHE_KEY];

  const type = get(job, 'jobParams.jobtrainingtype', 'RegularJob');
  let gpu = get(job, 'jobParams.resourcegpu', 0);
  if (type === 'PSDistJob') {
    gpu *= get(job, 'jobParams.numpsworker', 0);
  }
  return job[CACHE_KEY] = gpu;
};

export default (): Column<Job> => ({
  title: 'GPU',
  type: 'numeric',
  render(job) {
    return <>{valueOf(job)}</>;
  },
  customSort(job1, job2) {
    return valueOf(job1) - valueOf(job2);
  }
});
