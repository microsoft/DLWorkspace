import * as React from 'react';
import {
  FunctionComponent,
  useContext
} from 'react';

import {
  Button,
  makeStyles,
  createStyles,
} from '@material-ui/core';
import {
  AccountBox
} from '@material-ui/icons';

import UserContext from '../../contexts/User';

const useStyles = makeStyles(() => createStyles({
  'root': {
    whiteSpace: 'nowrap'
  }
}))

const UserButton: FunctionComponent = () => {
  const { givenName, familyName } = useContext(UserContext);
  const styles = useStyles();
  return (
    <Button
      variant="outlined"
      color="inherit"
      classes={styles}
      startIcon={<AccountBox/>}
    >
      {`${givenName} ${familyName}`}
    </Button>
  );
};

export default UserButton;
