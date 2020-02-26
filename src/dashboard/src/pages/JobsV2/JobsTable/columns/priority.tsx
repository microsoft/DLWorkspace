import React from 'react';
import { Column } from 'material-table';

import PriorityField from '../PriorityField';

import { Job } from '../../utils';

export default {
  title: 'Priority',
  type: 'numeric',
  render(job: Job) {
    return <PriorityField job={job}/>;
  },
  disableClick: true
} as Column<Job>;
