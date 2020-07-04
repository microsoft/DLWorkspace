import * as React from 'react';
import {
  FunctionComponent,
  useContext,
  useMemo,
} from 'react';

import { get } from 'lodash';

import {
  Box,
  BoxProps,
  Divider,
  Paper,
  Typography,
  createStyles,
  makeStyles,
} from '@material-ui/core';

import { Info } from '@material-ui/icons';

import ConfigContext from '../contexts/Config';
import TeamContext from '../contexts/Team';

const usePaperStyle = makeStyles(theme => createStyles({
  root: {
    display: 'flex',
    alignItems: 'center',
    padding: theme.spacing(1),
  },
}));

const NotificationBox: FunctionComponent<BoxProps> = (props) => {
  const { notifications } = useContext(ConfigContext);
  const { currentTeamId } = useContext(TeamContext);

  const notification = useMemo(() => {
    const notification = get(notifications, [currentTeamId]);
    if (notification === undefined) {
      return get(notifications, ['.default']);
    }
  }, [notifications, currentTeamId]);

  const paperStyle = usePaperStyle();

  if (Boolean(notification) === false) return null;

  return (
    <Box {...props}>
      <Paper elevation={0} classes={paperStyle}>
        <Info fontSize="small" color="primary"/>
        <Typography variant="body2" component={Box} flex={1} paddingLeft={1}>{notification}</Typography>
      </Paper>
      <Divider/>
    </Box>
  );
};

export default NotificationBox;
