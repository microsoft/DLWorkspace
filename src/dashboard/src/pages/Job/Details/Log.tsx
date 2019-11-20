import React, { useContext } from 'react';

import {
  Card,
  CardHeader,
  CardContent,
  Typography,
} from '@material-ui/core';

import Context from './Context';

const Log: React.FC = () => {
  const { job } = useContext(Context);
  return (
    <Card>
      <CardHeader title="Console Output"/>
      <CardContent>
        <Typography component='pre' style={{overflow:'auto'}}>{job['log']}</Typography>
      </CardContent>
    </Card>
  );
};

export default Log;
