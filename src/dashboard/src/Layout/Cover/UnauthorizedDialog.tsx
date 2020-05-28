import * as React from 'react';
import {
  FunctionComponent,
  useContext
} from 'react';

import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from '@material-ui/core';

import ConfigContext from '../../contexts/Config';

const UnauthorizedDialog: FunctionComponent = () => {
  const { addGroup } = useContext(ConfigContext);
  return (
    <Dialog open>
      <DialogTitle>Unauthorized User</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Please request to join a security group.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button component="a" href={addGroup} target="_blank" rel="noopener noreferrer" color="primary">
          Join Security Groups
        </Button>
        <Button href="/api/authenticate/logout" color="secondary">Sign Out</Button>
      </DialogActions>
    </Dialog>
  );
};

export default UnauthorizedDialog;
