import React from 'react';
import clsx from 'clsx';
import {
  makeStyles,
  useTheme,
  Theme,
  createStyles
} from '@material-ui/core/styles';
import {Box, CircularProgress, Toolbar} from '@material-ui/core';
import DrawerContext from '../Drawer/Context';
import TeamContext from '../../contexts/Teams';
const WIDTH = 240;
const useStyles = makeStyles((theme: Theme) =>
  createStyles({
    content: {
      flexGrow: 1,
      paddingLeft: theme.spacing(30),
      paddingTop: theme.spacing(3),
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
const Loading = (
  <Box flex={1} display="flex" alignItems="center" justifyContent="center">
    <CircularProgress/>
  </Box>
);
const Content: React.FC = ({ children }) => {
  const { open } = React.useContext(DrawerContext);
  const { teams } = React.useContext(TeamContext);
  const classes = useStyles();
  if (teams === undefined) {
    return Loading;
  } else {
    return (
      <Box
        className={clsx(classes.content, {
          [classes.contentShift]: open
        })}
      >
        <Toolbar />
        {children}
      </Box>
    )
  }

};

export default Content;
