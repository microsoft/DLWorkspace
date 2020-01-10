import React, { FunctionComponent, useMemo } from 'react';
import { capitalize } from 'lodash';
import { Chip, Tooltip } from '@material-ui/core';
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
  const status = useMemo<string>(() => job['jobStatus'], [job]);
  const icon = useMemo(() =>
    status === 'unapproved' ? <HourglassEmpty/>
    : status === 'queued' ? <HourglassEmpty/>
    : status === 'scheduling' ? <HourglassEmpty/>
    : status === 'running' ? <HourglassFull/>
    : status === 'finished' ? <CheckCircleOutline/>
    : status === 'failed' ? <ErrorOutline/>
    : status === 'pausing' ? <PauseCircleFilled/>
    : status === 'paused' ? <PauseCircleOutline/>
    : status === 'killing' ? <RemoveCircle/>
    : status === 'killed' ? <RemoveCircleOutline/>
    : <Help/>
  , [status]);
  const label = useMemo(() => capitalize(status), [status]);

  const detail = useMemo<Array<any>>(() => job['jobStatusDetail'], [job]);
  const titles = useMemo(() => {
    if (!Array.isArray(detail)) return [];

    return detail.map((d, index) => {
      if (typeof d.message === 'string') {
        return <div key={index}>{d.message}</div>
      } else {
        return <div key={index}>{JSON.stringify(d)}</div>
      }
    })
  }, [detail])
  return (
    <Tooltip title={titles} interactive>
      <Chip icon={icon} label={label}/>
    </Tooltip>
  );
}

export default JobStatus;
