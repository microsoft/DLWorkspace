import React from 'react';
import { Column } from 'material-table';

import { Job } from '../../utils';

export default {
  title: 'User',
  type: 'string',
  render(job: Job) {
    const user = job['userName'].split('@', 1)[0];
    return <>{user}</>;
  }
} as Column<Job>;
