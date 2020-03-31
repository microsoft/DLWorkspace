import { Column } from 'material-table';
import { get } from 'lodash';

import renderDate from './utils/renderDate';

import { Job } from '../../utils';

export default (): Column<Job> => ({
  title: 'Submitted',
  type: 'datetime',
  render(job) {
    const date = new Date(get(job, 'jobTime'));
    return renderDate(date);
  }
});
