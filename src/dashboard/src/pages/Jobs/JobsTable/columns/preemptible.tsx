import { Column } from 'material-table'

import { Job } from '../../../../utils/jobs'

export default (): Column<Job> => ({
  title: 'Preemptible',
  type: 'boolean',
  field: 'jobParams.preemptionAllowed'
})
