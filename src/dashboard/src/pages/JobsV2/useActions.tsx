import React, {
  useCallback,
  useState,
  useContext
} from 'react';
import {
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Snackbar,
  DialogActions,
  DialogContentText
} from '@material-ui/core';
import { Action } from 'material-table';

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

const useConfirm = () => {
  const [message, setMessage] = useState<string>();
  const [resolve, setResolve] = useState<(value: boolean) => void>();
  const confirm = useCallback((message: string) => {
    setMessage(message);
    return new Promise<boolean>((resolve) => {
      setResolve(() => resolve); // To avoid callbackify set-action
    });
  }, [setResolve, setMessage])
  const onNoClick = useCallback(() => {
    setMessage(undefined);
    if (resolve) resolve(false);
  }, [setMessage, resolve]);
  const onClose = onNoClick;
  const onYesClick = useCallback(() => {
    setMessage(undefined);
    if (resolve) resolve(true);
  }, [setMessage, resolve]);
  const dialog = (
    <Dialog open={message !== undefined} onClose={onClose}>
      <DialogTitle>Confirm</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button autoFocus color="primary" onClick={onNoClick}>No</Button>
        <Button onClick={onYesClick}>Yes</Button>
      </DialogActions>
    </Dialog>
  );
  return {
    confirm,
    dialog,
  }
}

const useAlert = () => {
  const [message, setMessage] = useState<string>();
  const alert = useCallback((message: string) => {
    setMessage(message);
  }, [setMessage]);
  const onClose = useCallback(() => {
    setMessage(undefined);
  }, [setMessage]);

  const snackbar = (
    <Snackbar
      open={message !== undefined}
      message={message}
      autoHideDuration={3000}
      onClose={onClose}
    />
  )

  return {
    alert,
    snackbar
  }
}

const useActions = () => {
  const { cluster } = useContext(ClusterContext);
  const { confirm, dialog } = useConfirm();
  const { alert, snackbar } = useAlert();

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

      return updateStatus(job.jobId, 'approved').then((response) => {
        if (response.ok) {
          alert(`${title} is being approved.`);
        } else {
          alert(`${title} is failed to approve.`);
        }
      });
    });
  }, [confirm, alert]);

  const onKill = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Kill job ${title} ?`).then((answer) => {
      if (answer === false) return;

      return updateStatus(job.jobId, 'killing').then((response) => {
        if (response.ok) {
          alert(`${title} is being killed.`);
        } else {
          alert(`${title} is failed to kill.`);
        }
      });
    });
  }, [confirm, alert]);

  const onPause = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Pause job ${title} ?`).then((answer) => {
      if (answer === false) return;

      return updateStatus(job.jobId, 'pausing').then((response) => {
        if (response.ok) {
          alert(`${title} is being paused.`);
        } else {
          alert(`${title} is failed to pause.`);
        }
      });
    });
  }, [confirm, alert]);

  const onResume = useCallback((event: any, job: any) => {
    const title = `${job.jobName}(${job.jobId})`;
    return confirm(`Resume job ${title} ?`).then((answer) => {
      if (answer === false) return;

      return updateStatus(job.jobId, 'queued').then((response) => {
        if (response.ok) {
          alert(`${title} is being resumed.`);
        } else {
          alert(`${title} is failed to resume.`);
        }
      });
    });
  }, [confirm, alert]);

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
  const component = (
    <>
      {dialog}
      {snackbar}
    </>
  );
  return { approve, kill, pause, resume, component };
}

export default useActions;
