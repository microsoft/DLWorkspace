import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Link as UILink } from '@material-ui/core';
import { Column } from 'material-table';

import { Job } from '../../utils';

export default {
  title: 'Name',
  field: 'jobName',
  render(job: Job) {
    return (
      <UILink variant="subtitle2" component={RouterLink} to={job['jobId']}>
        {job['jobName']}
      </UILink>
    );
  }
} as Column<Job>;
