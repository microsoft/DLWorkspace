import React from 'react';
import { Column } from 'material-table';

import JobStatus from '../../../../components/JobStatus';

import { Job } from '../../utils';

export default {
  title: 'Status',
  type: 'string',
  field: 'jobStatus',
  render(job: Job) {
    return <JobStatus job={job}/>;
  },
} as Column<Job>;
