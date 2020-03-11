import React, {
  FunctionComponent
} from 'react';
import clsx from 'clsx';

import {
  Box,
  Toolbar,
  Typography
} from '@material-ui/core';
import {
  Theme,
  createStyles,
  makeStyles
} from '@material-ui/core/styles';

import Loading from '../../components/Loading';
import TeamContext from '../../contexts/Teams';

import DrawerContext from '../Drawer/Context';

const WIDTH = 240;
const useStyles = makeStyles((theme: Theme) =>
  createStyles({
    content: {
      flexGrow: 1,
      maxWidth: '100%',
      paddingLeft: theme.spacing(30),
      paddingTop: theme.spacing(3),
      paddingBottom: theme.spacing(3),
      transition: theme.transitions.create('margin', {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.leavingScreen
      }),
      marginLeft: -WIDTH
    },
    contentShift: {
      transition: theme.transitions.create('margin', {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.enteringScreen
      }),
      marginLeft: 0
    }
  })
);

const Content: FunctionComponent = ({ children }) => {
  const { open } = React.useContext(DrawerContext);
  const { teams } = React.useContext(TeamContext);

  const classes = useStyles();

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
    <Box className={clsx(classes.content, { [classes.contentShift]: open })}>
      <Toolbar />
      {children}
    </Box>
  );
};

export default Content;
