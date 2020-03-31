import React from 'react';
import { Column } from 'material-table';
import { get } from 'lodash';

import { Job } from '../../utils';

export default (): Column<Job> => ({
  title: 'GPU',
  type: 'numeric',
  render(job) {
    const type = get(job, 'jobParams.jobtrainingtype', 'RegularJob');
    let gpu = get(job, 'jobParams.resourcegpu', 0);
    if (type === 'PSDistJob') {
      gpu *= get(job, 'jobParams.numpsworker', 0);
    }
    return <>{gpu}</>;
  }
});
