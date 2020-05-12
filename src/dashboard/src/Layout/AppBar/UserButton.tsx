import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useState
} from 'react';

import {
  Button,
  Dialog,
  DialogTitle,
  Divider,
  Link,
  List,
  ListItem,
  ListItemText,
  makeStyles,
  createStyles
} from '@material-ui/core';
import {
  AccountBox
} from '@material-ui/icons';

import UserContext from '../../contexts/User';
import TeamContext from '../../contexts/Team';

const useStyles = makeStyles(() => createStyles({
  'root': {
    whiteSpace: 'nowrap'
  }
}))

const UserButton: FunctionComponent = () => {
  const { email, password, givenName, familyName } = useContext(UserContext);
  const { currentTeamId } = useContext(TeamContext);
  const api = window.location.origin + `/api/teams/${currentTeamId}/jobs`
    + `?email=${encodeURIComponent(email || '')}&password=${encodeURIComponent(password || '')}`;
  const [open, setOpen] = useState(false);
  const handleClick = useCallback(() => {
    setOpen(true);
  }, []);
  const handleClose = useCallback(() => {
    setOpen(false);
  }, []);
  const styles = useStyles();
  return (
    <>
      <Button
        variant="outlined"
        color="inherit"
        classes={styles}
        startIcon={<AccountBox/>}
        onClick={handleClick}
      >
        {`${givenName} ${familyName}`}
      </Button>
      <Dialog
        maxWidth={false}
        open={open}
        onClose={handleClose}
      >
        <DialogTitle>User Account</DialogTitle>
        <Divider/>
        <List dense disablePadding>
          <ListItem>
            <ListItemText primary="Email" secondary={email}/>
          </ListItem>
          <ListItem>
            <ListItemText primary="Password" secondary={password}/>
          </ListItem>
          <Divider/>
          <ListItem>
            <ListItemText
              primary="Try an API"
              secondary={api}
              secondaryTypographyProps={{
                component: Link,
                href: api,
                target: '_blank',
                rel: 'noopener noreferrer'
              }}
            />
          </ListItem>
        </List>
      </Dialog>
    </>
  );
};

export default UserButton;
