import * as React from 'react'
import { Column } from 'material-table'

import { Job } from '../../utils'

export default (): Column<Job> => ({
  title: 'User',
  field: 'userName',
  render(job) {
    const user = job['userName'].split('@', 1)[0]
    return <>{user}</>
  }
})
