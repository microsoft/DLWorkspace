import React, {
  useCallback,
  useMemo,
  useState
} from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Link as UILink, Switch, Typography } from '@material-ui/core';
import { Column } from 'material-table';

import { Job } from '../../utils';

const useNameId = (): Column<Job> => {
  const [showId, setShowId] = useState(false);
  const onSwitchChange = useCallback((event: unknown, checked: boolean) => {
    setShowId(checked);
  }, []);

  const title = useMemo(() => (
    <>
      <Typography
        variant="inherit"
        color={showId ? "textSecondary" : "primary"}
      >
        Name
      </Typography>
      <Switch
        size="small"
        color="default"
        checked={showId}
        onChange={onSwitchChange}
      />
      <Typography
        variant="inherit"
        color={showId ? "primary" : "textSecondary"}
      >
        Id
      </Typography>
    </>
  ), [showId, onSwitchChange]);
  const field = useMemo(() => showId ? 'jobId' : 'jobName', [showId]);
  const render = useCallback((job: Job) => (
    <UILink
      variant="subtitle2"
      component={RouterLink}
      to={job['jobId']}
      style={showId ? { whiteSpace: 'nowrap' } : undefined}
    >
      {job[showId ? 'jobId' : 'jobName']}
    </UILink>
  ), [showId]);

  return { title, field, render };
}

export default useNameId;