import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
} from 'react';

import {
  Box,
  Button,
  Paper,
  Typography,
  createStyles,
  makeStyles,
} from '@material-ui/core'

import { Info } from '@material-ui/icons';

import useActions from '../../hooks/useActions';

import useRouteParams from './useRouteParams';
import Context from './Context';

const usePaperStyle = makeStyles(theme => createStyles({
  root: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: theme.spacing(1),
    padding: theme.spacing(1),
  },
}))

interface MessageProps {
  job: any;
  children: string;
}

const Message: FunctionComponent<MessageProps> = ({ children, job }) => {
  const { clusterId } = useRouteParams();
  const { support } = useActions(clusterId);
  const handleSupportClick = useCallback((event: any) => {
    support(job).onClick(event, job);
  }, [support, job]);
  const paperStyle = usePaperStyle();
  return (
    <Paper variant="outlined" classes={paperStyle}>
      <Info fontSize="small" color="primary"/>
      <Typography variant="body2" component={Box} flex={1} paddingLeft={1}>{children}</Typography>
      <Button size="small" color="primary" onClick={handleSupportClick}>support</Button>
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
          <Message key={index} job={job}>{message}</Message>
        ))
      }
    </>
  );
}

export default Insight;
