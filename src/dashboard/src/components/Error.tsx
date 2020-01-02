import React, { FunctionComponent, ReactNode } from 'react';

import { Box, SnackbarContent, makeStyles } from '@material-ui/core';
import { Error as ErrorIcon } from '@material-ui/icons';

const useSnackbarContentStyles = makeStyles((theme) => ({
  root: {
    backgroundColor: theme.palette.error.dark,
    color: theme.palette.error.contrastText
  },
  message: {
    display: "flex",
    alignItems: "center"
  },
  icon: {
    fontSize: 20,
    marginRight: theme.spacing(1)
  }
}));

const useIconStyles = makeStyles((theme) => ({
  root: {
    marginRight: theme.spacing(1)
  }
}));

interface Props {
  message: ReactNode;
}

const Error: FunctionComponent<Props> = ({ message }) => {
  const snackbarContentStyles = useSnackbarContentStyles();
  const iconStyles = useIconStyles();
  return (
    <Box p={2}>
      <SnackbarContent
        classes={snackbarContentStyles}
        message={
          <Box display="flex" alignItems="center">
            <ErrorIcon fontSize="small" classes={iconStyles}/>
            {message}
          </Box>
        }
      />
    </Box>
  );
};

export default Error;
