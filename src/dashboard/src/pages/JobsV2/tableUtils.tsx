import React from 'react';
import { Link as UILink } from '@material-ui/core';
import { Link as RouterLink } from 'react-router-dom';

import JobStatus from '../../components/JobStatus';

export const renderId = (job: any) => (
  <UILink to={job['jobId']} component={RouterLink}>
    {job['jobId']}
  </UILink>
)

const getGPU = (job: any) => {
  const type = job['jobParams']['jobtrainingtype'];
  if (type == null || type === 'RegularJob' || type === 'InferenceJob') {
    return job['jobParams']['resourcegpu']
  } else {
    return job['jobParams']['resourcegpu'] * job['jobParams']['numpsworker']
  }
}

export const renderGPU = (job: any) => <>{getGPU(job)}</>;
export const sortGPU = (jobA: any, jobB: any) => {
  return getGPU(jobA) - getGPU(jobB)
};

export const renderStatus = (job: any) => <JobStatus job={job}/>;

export const renderDate = (getter: (job: any) => Date) => (job: any) => {
  const date = getter(job);
  if (isNaN(date.valueOf())) return null;
  return <>{date.toLocaleString()}</>;
};

export const sortDate = (getter: (job: any) => Date) => (jobA: any, jobB: any) => {
  const dateA = getter(jobA);
  const dateB = getter(jobB);
  return dateA.valueOf() - dateB.valueOf();
};
