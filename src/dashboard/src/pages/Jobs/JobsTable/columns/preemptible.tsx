import { Column } from 'material-table';

import { Job } from '../../utils';

export default (): Column<Job> => ({
  title: 'Preemptible',
  type: 'boolean',
  field: 'jobParams.preemptionAllowed'
});
