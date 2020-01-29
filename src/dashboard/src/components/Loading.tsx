import React, { FunctionComponent } from 'react';

import { Box, CircularProgress } from '@material-ui/core';

const LoadingIndicator: FunctionComponent = () => (
  <Box p={2} display="flex" justifyContent="center">
    <CircularProgress/>
  </Box>
);

export default LoadingIndicator;
