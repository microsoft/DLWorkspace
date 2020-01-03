import React from 'react';

import JobStatus from '../../components/JobStatus';

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
