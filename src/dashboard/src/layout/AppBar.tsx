import React, {useCallback} from 'react';

import {
  AppBar,
  Box,
  Button,
  Grid,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
  Typography,
  Slide,
  Toolbar,
  ListItem,
  List,
  Divider,
  ListItemText,
  Dialog,
  Snackbar,
  SnackbarContent,
  Hidden
} from '@material-ui/core';
import { createStyles, makeStyles, Theme } from '@material-ui/core/styles';
import {
  AccountBox,
  Check,
  ExitToApp,
  Group,
  MenuRounded,
} from '@material-ui/icons';
import CloseIcon from '@material-ui/icons/Close';
import { TransitionProps } from '@material-ui/core/transitions';
import DrawerContext from './Drawer/Context';
import UserContext from '../contexts/User';
import TeamContext from '../contexts/Teams';
import { Link } from 'react-router-dom';
import _ from 'lodash';
import copy from 'clipboard-copy'
import {green,purple} from "@material-ui/core/colors";


const useStyles = makeStyles((theme: Theme) =>
  createStyles({
    headerStyle: {
      backgroundColor:theme.palette.background.paper,
    },
    leftIcon: {
      marginRight: theme.spacing(1)
    },
    success: {
      backgroundColor: green[600],
    },
    title: {
      padding: theme.spacing(1)
    },
    titleLink: {
      textDecoration: 'none',
      color:purple[50]
    },
    appBar: {
      zIndex: theme.zIndex.drawer + 1
    },
    userLabel: {
      whiteSpace:'nowrap'
    }

  })
);
const Transition = React.forwardRef<unknown, TransitionProps>(function Transition(props, ref) {
  return <Slide direction="up" ref={ref} {...props} />;
});
const OpenDrawerButton: React.FC = () => {
  const { setOpen, open } = React.useContext(DrawerContext);
  const onClick = React.useCallback(() => setOpen(!open), [setOpen, open]);
  return (
    <Tooltip title={"Go to pages"}>
      <IconButton edge="start" color="inherit" onClick={onClick}>
        <MenuRounded />
      </IconButton>
    </Tooltip>
  );
};

let TeamMenu: React.FC;
TeamMenu = () => {
  const { teams, saveSelectedTeam, selectedTeam } = React.useContext(
    TeamContext
  );

  const [open, setOpen] = React.useState(false);

  const button = React.useRef<any>(null);

  const onButtonClick = React.useCallback(() => setOpen(true), [setOpen]);
  const onMenuClose = React.useCallback(() => setOpen(false), [setOpen]);
  const onMenuItemClick = React.useCallback(
    team => () => {
      saveSelectedTeam(team);
      setOpen(false);
    },
    [saveSelectedTeam]
  );
  const styles = useStyles();
  return (
    <>
      <Button
        ref={button}
        variant="outlined"
        color="inherit"
        onClick={onButtonClick}
      >
        <Group className={styles.leftIcon} />
        {selectedTeam}
      </Button>
      <Menu anchorEl={button.current} open={open} onClose={onMenuClose}>
        {_.map(teams, 'id').map((team: string) => (
          <MenuItem
            key={team}
            disabled={team === selectedTeam}
            onClick={onMenuItemClick(team)}
          >
            {team === selectedTeam ? (
              <Check className={styles.leftIcon} />
            ) : (
              <Group className={styles.leftIcon} />
            )}
            <Typography variant="button">{team}</Typography>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

const UserButton: React.FC = () => {
  const [openUserProfile, setOpenUserProfile] = React.useState(false);
  const [openCopyWarn, setOpenCopyWarn] = React.useState(false);
  const { givenName, familyName,email,token } = React.useContext(UserContext);
  const styles = useStyles();
  const name = typeof email === 'string' ?  email.split('@', 1)[0] : email;
  const handleClose = () => {
    setOpenUserProfile(false);
  }
  const handleWarnClose = () => {
    setOpenCopyWarn(false);
  }
  const showUserProfile = () => {
    setOpenUserProfile(true);
  }

  const handleCopy = useCallback((value) => {
    copy(value);
    setOpenCopyWarn(true)
  },[])
  const classes = useStyles()
  return (
    <main>
      <Button variant="outlined" color="inherit" onClick={showUserProfile} className={classes.userLabel}>
        <AccountBox className={styles.leftIcon}/>
        {`${givenName} ${familyName}`}
      </Button>
      <Dialog fullScreen open={openUserProfile} onClose={handleClose} TransitionComponent={Transition}>
        <AppBar>
          <Toolbar>
            <IconButton edge="start" color="inherit" onClick={handleClose} aria-label="close">
              <CloseIcon />
            </IconButton>
            <Typography variant="h6">
              {"Account Settings"}
            </Typography>
          </Toolbar>
        </AppBar>
        <Box m={10}>
          <List>
            <ListItem button>
              <ListItemText primary="Email" secondary={email}  onClick={()=>handleCopy(email)}/>
            </ListItem>
            <Divider />
            <ListItem button>
              <ListItemText primary="Username" secondary={name}  onClick={()=>handleCopy(name)}/>
            </ListItem>
            <Divider />
            <ListItem button >
              <ListItemText primary="Password" secondary={token} onClick={()=>handleCopy(token)}/>
            </ListItem>
          </List>
        </Box>
        <Snackbar
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          open={openCopyWarn}
          autoHideDuration={500}
          onClose={handleWarnClose}
          ContentProps={{
            'aria-describedby': 'message-id',
          }}
        >
          <SnackbarContent
            className={styles.success}
            aria-describedby="client-snackbar"
            message={<span id="message-id" >Copied Success</span>}
          />
        </Snackbar>
      </Dialog>

    </main>
  );
};
const clearLocalStorage = () => {
  localStorage.clear()
}
const SignOutButton: React.FC = () => {
  return (
    <Tooltip title="Sign Out">
      <IconButton edge="end" color="inherit" onClick={clearLocalStorage} href="/api/authenticate/logout">
        <ExitToApp />
      </IconButton>
    </Tooltip>
  );
};

const Title: React.FC = () => {
  const styles = useStyles();
  return (
    <Box component="header" className={styles.title} display="flex">
      <Link to="/" className={styles.titleLink}>
        <Typography component="h1" variant="h6" align="left">
          DLTS
        </Typography>
      </Link>
    </Box>
  );
};

const DashboardAppBar: React.FC = () => {
  const styles = useStyles();
  //const { open } = React.useContext(DrawerContext);
  return (
    <AppBar
      component="aside"
      position="fixed"
      className={styles.appBar}
    >
      <Toolbar>
        <Grid
          container
          wrap="nowrap"
          justify="flex-end"
          alignItems="center"
        >
          <Grid item>
            <OpenDrawerButton />
          </Grid>
          <Hidden xsDown>
            <Grid item xs>
              <Title />
            </Grid>
          </Hidden>
          <Grid item >
            <TeamMenu />
          </Grid>
          <Grid item style={{ marginLeft:'5' }}>
            <UserButton />
          </Grid>
          <Grid item>
            {' '}
            <SignOutButton />
          </Grid>
        </Grid>
      </Toolbar>
    </AppBar>
  );
};

export default DashboardAppBar;
