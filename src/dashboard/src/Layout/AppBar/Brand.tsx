import * as React from 'react';
import {
  FunctionComponent
} from 'react';

import { Link } from 'react-router-dom';

import {
  Box,
  Tooltip,
  Typography,
  Link as UILink,
} from '@material-ui/core';

const Brand: FunctionComponent = () => (
  <Box p={1}>
    <Typography component="h1" variant="h6" align="left">
      <Tooltip title="Back to index page" placement="right">
        <UILink color="inherit" component={Link} to="/">
          DLTS
        </UILink>
      </Tooltip>
    </Typography>
  </Box>
);

export default Brand;
