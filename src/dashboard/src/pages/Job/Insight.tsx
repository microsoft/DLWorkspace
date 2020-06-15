import * as React from 'react';
import {
  FunctionComponent,
  useContext,
  useMemo,
} from 'react';

import {
  Box,
  Paper,
  Typography,
  createStyles,
  makeStyles,
} from '@material-ui/core'

import { Info } from '@material-ui/icons';

import Context from './Context';

const usePaperStyle = makeStyles(theme => createStyles({
  root: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: theme.spacing(1),
    padding: theme.spacing(1),
  },
}))

const Message: FunctionComponent<{ children: string }> = ({ children }) => {
  const paperStyle = usePaperStyle();
  return (
    <Paper variant="outlined" classes={paperStyle}>
      <Info fontSize="small" color="primary"/>
      <Typography variant="body2" component={Box} flex={1} paddingLeft={1}>{children}</Typography>
    </Paper>
  );
}

const Insight: FunctionComponent = () => {
  const { job } = useContext(Context);

  const messages = useMemo(() => {
    if (job == null) return [];
    if (job['insight'] == null) return [];
    if (!Array.isArray(job['insight']['messages'])) return [];
    return job['insight']['messages'];
  }, [job]);

  return (
    <>
      {
        messages.map((message, index) => (
          <Message key={index}>{message}</Message>
        ))
      }
    </>
  );
}

export default Insight;
