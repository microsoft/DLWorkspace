import React from 'react';

export const renderDate = (getter: (job: any) => Date) => (job: any) => {
  const date = getter(job);
  if (isNaN(date.valueOf())) return <>N/A</>;
  return <>{date.toLocaleString()}</>;
};

export const sortDate = (getter: (job: any) => Date) => (jobA: any, jobB: any) => {
  const dateA = getter(jobA);
  const dateB = getter(jobB);
  return dateA.valueOf() - dateB.valueOf();
};
