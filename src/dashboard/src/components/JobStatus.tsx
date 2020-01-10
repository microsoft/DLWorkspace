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
  const title = useMemo(() => {
    if (!Array.isArray(detail)) return null;
    if (detail.length === 0) return null;
    const firstDetail = detail[0];
    if (typeof firstDetail !== 'object') return null;
    const firstDetailMessage = firstDetail.message;
    if (typeof firstDetailMessage === 'string') return firstDetailMessage;
    if (typeof firstDetailMessage === 'object') return (
      <pre>{JSON.stringify(firstDetailMessage, null, 2)}</pre>
    );
    return <pre>{JSON.stringify(firstDetail, null, 2)}</pre>;
  }, [detail]);
  return (
    <Tooltip title={title} placement="right" interactive>
      <Chip icon={icon} label={label}/>
    </Tooltip>
  );
}

export default JobStatus;
