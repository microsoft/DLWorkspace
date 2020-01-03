import React, { FunctionComponent } from 'react';
import { Chip } from '@material-ui/core';
import {
  HourglassEmpty,
  HourglassFull,
  CheckCircleOutline,
  ErrorOutline,
  PauseCircleFilled,
  PauseCircleOutline,
  RemoveCircle,
  RemoveCircleOutline,
  Help
} from '@material-ui/icons';

interface Props {
  job: any;
}

const JobStatus: FunctionComponent<Props> = ({ job }) => {
  const status = job['jobStatus'];
  const icon = status === 'unapproved' ? <HourglassEmpty/>
    : status === 'queued' ? <HourglassEmpty/>
    : status === 'scheduling' ? <HourglassEmpty/>
    : status === 'running' ? <HourglassFull/>
    : status === 'finished' ? <CheckCircleOutline/>
    : status === 'failed' ? <ErrorOutline/>
    : status === 'pausing' ? <PauseCircleFilled/>
    : status === 'paused' ? <PauseCircleOutline/>
    : status === 'killing' ? <RemoveCircle/>
    : status === 'killed' ? <RemoveCircleOutline/>
    : <Help/>;
  const label = status[0].toUpperCase() + status.slice(1)
  return <Chip icon={icon} label={label}/>;
}

export default JobStatus;
