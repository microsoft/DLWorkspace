import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Link as UILink } from '@material-ui/core';
import { Column } from 'material-table';

import { Job } from '../../utils';

export default {
  title: 'Name',
  type: 'string',
  field: 'jobName',
  render(job: Job) {
    return (
      <RouterLink to={job['jobId']} component={UILink}>
        {job['jobName']}
      </RouterLink>
    );
  }
} as Column<Job>;
