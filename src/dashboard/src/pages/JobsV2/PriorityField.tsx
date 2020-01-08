import React, {
  FunctionComponent,
  KeyboardEvent,
  useCallback,
  useContext,
  useMemo,
  useState,
  useRef
} from 'react';
import { Button, TextField } from '@material-ui/core';
import { useSnackbar } from 'notistack';

import ClusterContext from './ClusterContext';

interface Props {
  job: any;
}

const PriorityField: FunctionComponent<Props> = ({ job }) => {
  const { enqueueSnackbar } = useSnackbar();
  const { cluster } = useContext(ClusterContext);
  const [editing, setEditing] = useState(false);
  const [textFieldDisabled, setTextFieldDisabled] = useState(false);
  const input = useRef<HTMLInputElement>();
  const buttonEnabled = useMemo(() => {
    return (
      job['jobStatus'] === 'running' ||
      job['jobStatus'] === 'queued' ||
      job['jobStatus'] === 'scheduling' ||
      job['jobStatus'] === 'unapproved' ||
      job['jobStatus'] === 'paused' ||
      job['jobStatus'] === 'pausing'
    )
  }, [job])
  const priority = useMemo(() => {
    if (job['priority'] == null) {
      return 100;
    }
    return job['priority'];
  }, [job])
  const setPriority = useCallback((priority: number) => {
    if (priority === job['priority']) return;
    enqueueSnackbar('Priority is being set...');
    setTextFieldDisabled(true);

    fetch(`/api/clusters/${cluster.id}/jobs/${job['jobId']}/priority`, {
      method: 'PUT',
      body: JSON.stringify({ priority }),
      headers: { 'Content-Type': 'application/json' }
    }).then((response) => {
      if (response.ok) {
        enqueueSnackbar('Priority is set successfully', { variant: 'success' });
      } else {
        throw Error();
      }
      setEditing(false);
    }).catch(() => {
      enqueueSnackbar('Failed to set priority', { variant: 'error' });
    }).then(() => {
      setTextFieldDisabled(false);
    });
  }, [enqueueSnackbar, job, cluster.id]);
  const onBlur = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    setEditing(false);
    if (input.current) {
      setPriority(input.current.valueAsNumber);
    }
  }, [setPriority]);
  const onKeyDown = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && input.current) {
      setPriority(input.current.valueAsNumber);
    }
    if (event.key === 'Escape') {
      setEditing(false);
    }
  }, [setPriority, setEditing]);
  const onClick = useCallback(() => {
    setEditing(true);
  }, [setEditing])

  if (editing) {
    return (
      <TextField
        inputRef={input}
        type="number"
        defaultValue={priority}
        disabled={textFieldDisabled}
        fullWidth
        onBlur={onBlur}
        onKeyDown={onKeyDown}
      />
    );
  } else {
    return (
      <Button
        fullWidth
        variant={buttonEnabled ? 'outlined' : 'text'}
        onClick={buttonEnabled ? onClick : undefined}
      >
        {priority}
      </Button>
    );
  }
};

export default PriorityField;
