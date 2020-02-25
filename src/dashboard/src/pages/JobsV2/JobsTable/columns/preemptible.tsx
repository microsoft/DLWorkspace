import { Column } from 'material-table';

import { Job } from '../../utils';

export default {
  title: 'Preemptible',
  type: 'boolean',
  field: 'jobParams.preemptionAllowed'
} as Column<Job>;
