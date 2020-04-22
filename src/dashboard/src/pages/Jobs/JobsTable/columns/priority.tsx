import React from 'react';
import { Column } from 'material-table';

import PriorityField from '../PriorityField';

import { Job } from '../../utils';

const valueOf = (job: Job): number => {
  return job['priority'] != null ? job['priority'] : 100;
};

export default (): Column<Job> => ({
  title: 'Priority',
  type: 'numeric',
  render(job) {
    return <PriorityField job={job}/>;
  },
  customSort(job1, job2) {
    return valueOf(job1) - valueOf(job2)
  }
});
