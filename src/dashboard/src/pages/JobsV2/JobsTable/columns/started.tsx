import React from 'react';
import { Column } from 'material-table';
import { get } from 'lodash';

import { Job } from '../../utils';

export default {
  title: 'Started',
  type: 'datetime',
  render(job: Job) {
    const date = new Date(get(job, 'jobStatusDetail.0.startedAt'));
    if (isNaN(date.valueOf())) return null;
    return <>{date.toLocaleString()}</>;
  }
} as Column<Job>;
