import { Column } from 'material-table';
import { get } from 'lodash';

import renderDate from './utils/renderDate';

import { Job } from '../../utils';

export default (): Column<Job> => ({
  title: 'Started',
  type: 'datetime',
  render(job) {
    const date = new Date(get(job, 'jobStatusDetail.0.startedAt'));
    return renderDate(date);
  }
});
