import * as React from 'react';
import {
  FunctionComponent,
  SyntheticEvent,
  useCallback,
  useContext,
  useMemo,
} from 'react';

import { get } from 'lodash';

import {
  Box,
  Button,
  Paper,
  Typography,
  createStyles,
  makeStyles,
  useTheme,
} from '@material-ui/core'
import {
  Info,
  Warning,
} from '@material-ui/icons';

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
}));

interface DiagnosticProps {
  level: string;
  action: string;
  children: string;
}

const Diagnostic: FunctionComponent<DiagnosticProps> = ({ level, action, children }) => {
  const { clusterId } = useRouteParams();
  const { job } = useContext(Context);
  const { kill } = useActions(clusterId);
  const { palette } = useTheme();

  const handleKillClick = useCallback((event: SyntheticEvent) => {
    kill(job).onClick(event, job);
  }, [kill, job]);

  const icon = useMemo(() => {
    if (level === 'WARNING') {
      return <Warning fontSize="large" htmlColor={palette.warning.main}/>;
    } else { // 'INFO' by default
      return <Info fontSize="large" htmlColor={palette.info.main}/>;
    }
  }, [level, palette]);
  const button = useMemo(() => {
    if (action === 'KillJob') {
      return <Button size="large" color="secondary" onClick={handleKillClick}>Kill</Button>;
    }
  }, [action, handleKillClick]);

  const paperStyle = usePaperStyle();
  return (
    <Paper variant="outlined" classes={paperStyle}>
      {icon}
      <Typography variant="body2" component={Box} flex={1} paddingLeft={1}>{children}</Typography>
      {button}
    </Paper>
  );
}

const Insight: FunctionComponent = () => {
  const { job } = useContext(Context);

  const diagnostics = useMemo<any[]>(() => {
    return get(job, ['insight', 'diagnostics'], []);
  }, [job]);

  return (
    <>
      {
        diagnostics.map(([level, text, action]: [string, string, string], index) => (
          <Diagnostic key={index} level={level} action={action}>{text}</Diagnostic>
        ))
      }
    </>
  );
}

export default Insight;
