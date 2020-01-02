import React, {
  useCallback,
  useContext
} from 'react';
import { useSnackbar } from 'notistack';
import { Action } from 'material-table';

import useConfirm from '../../components/useConfirm';

import ClusterContext from './ClusterContext';

const APPROVABLE_STATUSES = [
  'unapproved'
];
const KILLABLE_STATUSES = [
  'unapproved',
  'queued',
  'scheduling',
  'running',
  'pausing',
  'paused'
];
const PAUSABLE_STATUSES = [
  'queued',
  'scheduling',
  'running'
];
const RESUMABLE_STATUSES = [
  'paused'
];

const useActions = () => {
  const { cluster } = useContext(ClusterContext);
  const { confirm, dialog } = useConfirm();
  const { enqueueSnackbar } = useSnackbar();

  const updateStatus = useCallback((jobId: string, status: string) => {
    const url = `/api/clusters/${cluster.id}/jobs/${jobId}/status`;
    return fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status })
    })
  }, [cluster.id])

  const onApprove = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Approve job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being approved.`);
      return updateStatus(job.jobId, 'approved').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title} is approved.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to approve.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar]);

  const onKill = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Kill job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being killed.`);
      return updateStatus(job.jobId, 'killing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title} is killed.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to kill.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar]);

  const onPause = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Pause job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being paused.`);
      return updateStatus(job.jobId, 'pausing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title} is paused.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to pause.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar]);

  const onResume = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Resume job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being resumed.`);
      return updateStatus(job.jobId, 'queued').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title} is resumed.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to resume.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar]);

  const approve = useCallback((job: any): Action<any> => {
    const hidden = APPROVABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'check',
      tooltip: 'Approve',
      onClick: onApprove
    }
  }, []);
  const kill = useCallback((job: any): Action<any> => {
    const hidden = KILLABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'clear',
      tooltip: 'Kill',
      onClick: onKill
    }
  }, []);
  const pause = useCallback((job: any): Action<any> => {
    const hidden = PAUSABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'pause',
      tooltip: 'Pause',
      onClick: onPause
    }
  }, []);
  const resume = useCallback((job: any): Action<any> => {
    const hidden = RESUMABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'play_arrow',
      tooltip: 'Resume',
      onClick: onResume
    }
  }, []);
  const component = dialog;
  return { approve, kill, pause, resume, component };
}

export default useActions;
