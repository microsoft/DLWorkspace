import React, {
  FunctionComponent
} from 'react';

import {
  Box,
  Toolbar,
  Typography,
  createStyles,
  makeStyles
} from '@material-ui/core';

import Loading from '../../components/Loading';
import TeamContext from '../../contexts/Teams';

import DrawerContext, { WIDTH } from '../Drawer/Context';

const useStyles = makeStyles(theme => createStyles<
  'root',
  { open: boolean }
>({
  root: {
    flexGrow: 1,
    maxWidth: '100%',
    paddingLeft: theme.spacing(30),
    paddingTop: theme.spacing(3),
    paddingBottom: theme.spacing(3),
    transition: ({ open }) => theme.transitions.create('margin', {
      easing: open
        ? theme.transitions.easing.easeOut
        : theme.transitions.easing.sharp,
      duration: open
        ? theme.transitions.duration.enteringScreen
        : theme.transitions.duration.leavingScreen
    }),
    marginLeft: ({ open }) => open ? 0 : -WIDTH
  }
}));

const Content: FunctionComponent = ({ children }) => {
  const { open } = React.useContext(DrawerContext);
  const { teams } = React.useContext(TeamContext);

  const classes = useStyles({ open });

  if (teams === undefined) {
    return (
      <Box
        flex={1}
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
      >
        <Loading/>
        <Typography component="p" variant="subtitle1">Fetching Teams</Typography>
      </Box>
    );
  }

  return (
    <Box className={classes.root}>
      <Toolbar />
      {children}
    </Box>
  );
};

export default Content;
