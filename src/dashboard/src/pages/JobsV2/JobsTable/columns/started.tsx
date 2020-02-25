import { Column } from 'material-table';
import { get } from 'lodash';

import renderDate from './renderDate';

import { Job } from '../../utils';

export default {
  title: 'Started',
  type: 'datetime',
  render(job: Job) {
    const date = new Date(get(job, 'jobStatusDetail.0.startedAt'));
    return renderDate(date);
  }
} as Column<Job>;
