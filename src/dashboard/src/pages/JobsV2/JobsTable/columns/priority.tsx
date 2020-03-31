import React from 'react';
import { Column } from 'material-table';

import PriorityField from '../PriorityField';

import { Job } from '../../utils';

export default (): Column<Job> => ({
  title: 'Priority',
  type: 'numeric',
  render(job) {
    return <PriorityField job={job}/>;
  },
  disableClick: true
});
