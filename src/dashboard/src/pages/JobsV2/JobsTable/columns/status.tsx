import React, { useContext, FunctionComponent } from 'react';
import { Column } from 'material-table';

import JobStatus from '../../../../components/JobStatus';
import ClusterContext from '../../ClusterContext';

import { Job } from '../../utils';

const JobStatusColumn: FunctionComponent<{ job: Job }> = ({ job }) => {
  const { cluster } = useContext(ClusterContext);
  return <JobStatus cluster={cluster.id} job={job}/>;
}

export default {
  title: 'Status',
  field: 'jobStatus',
  render(job: Job) {
    return <JobStatusColumn job={job}/>
  },
} as Column<Job>;
