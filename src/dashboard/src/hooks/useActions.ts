import { useCallback, useContext } from 'react';
import { useSnackbar } from 'notistack';
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

  const batchUpdateStatus = useCallback((jobIds: string[], statusValue: string) => {
    const url = `/api/clusters/${clusterId}/jobs/status`;
    const status = Object.create(null);
    for (const jobId of jobIds) {
      status[jobId] = statusValue
    }
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status })
    })
  }, [clusterId]);

  const onSupport = useCallback((event: any, job: any) => {
    const subject = `[DLTS Job][${clusterId}][${job['vcName']}]: <Issue Title by User>`;
    const body = `
Hi DLTS support team,

There is some issue in my job ${window.location.origin}/jobs-v2/${encodeURIComponent(clusterId)}/${encodeURIComponent(job['jobId'])}

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

  const onBatchApprove = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} jobs`;
    return confirm(`Approve ${title}?`).then((answer) => {
      if (answer === false) return;

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being approved.`);
      return batchUpdateStatus(jobIds, 'approved').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s approve request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} are failed to approve.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, batchUpdateStatus]);

  const onBatchPause = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} jobs`;
    return confirm(`Pause ${title}?`).then((answer) => {
      if (answer === false) return;

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being paused.`);
      return batchUpdateStatus(jobIds, 'pausing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s pause request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} are failed to pause.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, batchUpdateStatus]);

  const onBatchResume = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} jobs`;
    return confirm(`Resume ${title}?`).then((answer) => {
      if (answer === false) return;

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being resumed.`);
      return batchUpdateStatus(jobIds, 'queued').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s resume request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} are failed to resume.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, batchUpdateStatus]);

  const onBatchKill = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} jobs`;
    return confirm(`Kill ${title}?`).then((answer) => {
      if (answer === false) return;

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being killed.`);
      return batchUpdateStatus(jobIds, 'killing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s kill request is accepted.`, { variant: 'success' });
        } else {
          enqueueSnackbar(`${title} are failed to kill.`, { variant: 'error' });
        }
      });
    });
  }, [confirm, enqueueSnackbar, batchUpdateStatus]);

  const support = useCallback(Object.assign((job: any): Action<any> => {
    return {
      icon: 'help',
      tooltip: 'Support',
      onClick: onSupport
    };
  }, { position: 'row' }), [onSupport]);

  const approve = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = APPROVABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'check',
      tooltip: 'Approve',
      onClick: onApprove
    }
  }, { position: 'row' }), [onApprove]);
  const pause = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = PAUSABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'pause',
      tooltip: 'Pause',
      onClick: onPause
    }
  }, { position: 'row' }), [onPause]);
  const resume = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = RESUMABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'play_arrow',
      tooltip: 'Resume',
      onClick: onResume
    }
  }, { position: 'row' }), [onResume]);
  const kill = useCallback(Object.assign((job: any): Action<any> => {
    const hidden = KILLABLE_STATUSES.indexOf(job['jobStatus']) === -1;
    return {
      hidden,
      icon: 'clear',
      tooltip: 'Kill',
      onClick: onKill
    }
  }, { position: 'row' }), [onKill]);

  const batchApprove = useCallback(Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => APPROVABLE_STATUSES.indexOf(job['jobStatus']) === -1);
    return {
      hidden,
      icon: 'check',
      tooltip: 'Approve',
      onClick: onBatchApprove
    }
  }, { position: 'toolbarOnSelect' }), [onBatchApprove]);
  const batchPause = useCallback(Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => PAUSABLE_STATUSES.indexOf(job['jobStatus']) === -1);
    return {
      hidden,
      icon: 'pause',
      tooltip: 'Pause',
      onClick: onBatchPause
    }
  }, { position: 'toolbarOnSelect' }), [onBatchPause]);
  const batchResume = useCallback(Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => RESUMABLE_STATUSES.indexOf(job['jobStatus']) === -1);
    return {
      hidden,
      icon: 'play_arrow',
      tooltip: 'Resume',
      onClick: onBatchResume
    }
  }, { position: 'toolbarOnSelect' }), [onBatchResume]);
  const batchKill = useCallback(Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => KILLABLE_STATUSES.indexOf(job['jobStatus']) === -1);
    return {
      hidden,
      icon: 'clear',
      tooltip: 'Kill',
      onClick: onBatchKill
    }
  }, { position: 'toolbarOnSelect' }), [onBatchKill]);

  return {
    support,
    approve, pause, resume, kill,
    batchApprove, batchPause, batchResume, batchKill
  };
}

export default useActions;
