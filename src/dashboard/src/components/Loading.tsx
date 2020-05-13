import React, { FunctionComponent } from 'react';

import { Box, CircularProgress, Typography } from '@material-ui/core';

interface LoadingProps {
  children?: string;
}

const Loading: FunctionComponent<LoadingProps> = ({ children }) => (
  <Box
    flex={1} alignSelf="center"
    display="flex" flexDirection="column" justifyContent="center" alignItems="center"
    p={2}
  >
    <CircularProgress/>
    {children && <Typography variant="caption" children={children}/>}
  </Box>
);

export default Loading;
