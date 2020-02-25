import { Column } from 'material-table';
import { get } from 'lodash';

import { Job } from '../../utils';

import renderDate from './renderDate';

export default {
  title: 'Finished',
  type: 'datetime',
  render(job: Job) {
    const date = new Date(get(job, 'jobStatusDetail.0.finishedAt'));
    return renderDate(date);
  }
} as Column<Job>;
