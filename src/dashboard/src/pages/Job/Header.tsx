import * as React from 'react';
import {
  FunctionComponent,
  createElement,
  useContext,
  useMemo,
} from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  IconButton,
  Toolbar,
  Typography,
  Tooltip
} from '@material-ui/core';
import {
  ArrowBack
} from '@material-ui/icons';

import useActions from '../../hooks/useActions';
import JobStatus from '../../components/JobStatus';

import useRouteParams from './useRouteParams';
import Context from './Context';

const Header: FunctionComponent<{ manageable: boolean }> = ({ manageable }) => {
  const { clusterId } = useRouteParams();
  const { accessible, admin, job } = useContext(Context);
  const { support, approve, kill, pause, resume } = useActions(clusterId);

  const availableActions = useMemo(() => {
    const actions = [support];
    if (manageable && admin) actions.push(approve);
    if (manageable) actions.push(pause, resume, kill);
    return actions;
  }, [manageable, admin, support, approve, kill, pause, resume]);

  const actionButtons = availableActions.map((action, index) => {
    const { hidden, icon, tooltip, onClick } = action(job);
    if (hidden) return null;
    return (
      <Tooltip key={index} title={tooltip as string}>
        <IconButton onClick={(event) => onClick(event, job)}>
          {createElement(icon)}
        </IconButton>
      </Tooltip>
    )
  })

  return (
    <Toolbar disableGutters variant="dense">
      {accessible && (
        <IconButton
          edge="start"
          color="inherit"
          component={Link}
          to="./"
        >
          <ArrowBack />
        </IconButton>
      )}
      <Typography variant="h6">
        {job['jobName']}
      </Typography>
      <Box flexGrow={1} paddingX={1}>
        <JobStatus cluster={clusterId} job={job}/>
      </Box>
      {actionButtons}
    </Toolbar>
  );
}

export default Header;
