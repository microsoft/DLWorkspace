import { Column } from 'material-table';
import { get } from 'lodash';

import { Job } from '../../utils';

import renderDate from './utils/renderDate';

export default (): Column<Job> => ({
  title: 'Finished',
  type: 'datetime',
  render(job) {
    const date = new Date(get(job, 'jobStatusDetail.0.finishedAt'));
    return renderDate(date);
  }
});
