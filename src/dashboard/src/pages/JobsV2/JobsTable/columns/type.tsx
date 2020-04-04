import { Column } from 'material-table';
import { Job } from '../../utils';

export default (): Column<Job> => ({
  title: 'Type',
  field: 'jobParams.jobtrainingtype'
});
