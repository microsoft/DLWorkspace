import { Column } from 'material-table';
import { get } from 'lodash';

import renderDate from './renderDate';

import { Job } from '../../utils';

export default {
  title: 'Submitted',
  type: 'datetime',
  render(job: Job) {
    const date = new Date(get(job, 'jobTime'));
    return renderDate(date);
  }
} as Column<Job>;
