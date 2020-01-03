import React from 'react';

import {
  Chip
} from '@material-ui/core';

import {
  HourglassEmpty,
  HourglassFull,
  CheckCircleOutline,
  Error,
  PauseCircleFilled,
  PauseCircleOutline,
  RemoveCircle,
  RemoveCircleOutline,
  Help
} from '@material-ui/icons';

export const renderStatus = (job: any) => {
  const status = job['jobStatus'];
  const icon = status === 'unapproved' ? <HourglassEmpty/>
    : status === 'queued' ? <HourglassEmpty/>
    : status === 'scheduling' ? <HourglassEmpty/>
    : status === 'running' ? <HourglassFull/>
    : status === 'finished' ? <CheckCircleOutline/>
    : status === 'failed' ? <Error/>
    : status === 'pausing' ? <PauseCircleFilled/>
    : status === 'paused' ? <PauseCircleOutline/>
    : status === 'killing' ? <RemoveCircle/>
    : status === 'killed' ? <RemoveCircleOutline/>
    : <Help/>;
  const label = status[0].toUpperCase() + status.slice(1)
  return <Chip icon={icon} label={label}/>;
}

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
