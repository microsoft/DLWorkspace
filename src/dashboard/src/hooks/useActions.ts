import { createElement, useCallback, useContext } from 'react';
import { useSnackbar } from 'notistack';
import { Check, Clear, ContactSupport, Pause, PlayArrow } from '@material-ui/icons';
import { Action } from 'material-table';

import ConfigContext from '../contexts/Config';
import UserContext from '../contexts/User';

import useConfirm from './useConfirm';

const APPROVABLE_STATUSES = [
  'unapproved'
];
const PAUSABLE_STATUSES = [
  'queued',
  'scheduling',
  'running'
];
const RESUMABLE_STATUSES = [
  'paused'
];
const KILLABLE_STATUSES = [
  'unapproved',
  'queued',
  'scheduling',
  'running',
  'pausing',
  'paused'
];

const useActions = (clusterId: string) => {
  const { familyName, givenName } = useContext(UserContext);
  const { support: supportMail } = useContext(ConfigContext);
  const confirm = useConfirm();
  const { enqueueSnackbar } = useSnackbar();

  const updateStatus = useCallback((jobId: string, status: string) => {
    const url = `/api/clusters/${clusterId}/jobs/${jobId}/status`;
    return fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status })
    })
  }, [clusterId]);

  const onSupport = useCallback((event: any, job: any) => {
    const subject = `[DLTS Job][${clusterId}][${job['vcName']}][${job['jobId']}]: <Issue Title by User>`
    const body = `
Hi DLTS support team,

There is some issue in my job ${window.location.origin}/jobs/${encodeURIComponent(clusterId)}/${encodeURIComponent(job['jobId'])}

<Issue description by user>

Thanks,
${givenName} ${familyName}
    `.trim();
    const link = `mailto:${supportMail || ''}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(link);
  }, [clusterId, supportMail, familyName, givenName]);

  const onApprove = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Approve job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being approved.`);
      return updateStatus(job.jobId, 'approved').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s approve request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to approve.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, updateStatus]);

  const onPause = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Pause job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being paused.`);
      return updateStatus(job.jobId, 'pausing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s pause request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to pause.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, updateStatus]);

  const onResume = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Resume job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being resumed.`);
      return updateStatus(job.jobId, 'queued').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s resume request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to resume.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, updateStatus]);

  const onKill = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Kill job ${title} ?`).then((answer) => {
      if (answer === false) return;

      enqueueSnackbar(`${title} is being killed.`);
      return updateStatus(job.jobId, 'killing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s kill request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} is failed to kill.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, updateStatus]);

  const support = useCallback(Object.assign((job: any): Action<any> => {
    return {
      icon: () => createElement(ContactSupport),
      tooltip: 'Support',
      onClick: onSupport
    };
  }, { position: 'row' }), [onSupport]);

  const approve = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = APPROVABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: () => createElement(Check),
      tooltip: 'Approve',
      onClick: onApprove
    }
  }, { position: 'row' }), [onApprove]);

  const pause = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = PAUSABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: () => createElement(Pause),
      tooltip: 'Pause',
      onClick: onPause
    }
  }, { position: 'row' }), [onPause]);

  const resume = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = RESUMABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: () => createElement(PlayArrow),
      tooltip: 'Resume',
      onClick: onResume
    }
  }, { position: 'row' }), [onResume]);

  const kill = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = KILLABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: () => createElement(Clear),
      tooltip: 'Kill',
      onClick: onKill
    }
  }, { position: 'row' }), [onKill]);

  return { support, approve, pause, resume, kill };
}

export default useActions;
