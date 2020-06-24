import * as React from 'react';
import {
  FunctionComponent,
  SyntheticEvent,
  useCallback,
  useContext,
  useMemo,
  useState,
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
import { formatDateDistance } from '../../utils/formats';

import useRouteParams from './useRouteParams';
import Context from './Context';

const usePaperStyle = makeStyles(theme => createStyles({
  root: (collapse: boolean) => collapse ? {
    display: 'flex',
    alignItems: 'center',
    marginBottom: theme.spacing(1),
    padding: theme.spacing(1),
  } : {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'stretch',
    marginBottom: theme.spacing(1),
    padding: theme.spacing(1),
  },
}));

const useTypographyStyle = makeStyles(theme => createStyles({
  root: (collapsed) => collapsed ? {
    overflowX: 'hidden',
    whiteSpace: 'nowrap',
    textOverflow: 'ellipsis'
  } : {},
}));

interface DiagnosticProps {
  date: Date;
  level: string;
  action: string;
  children: string;
}

const Diagnostic: FunctionComponent<DiagnosticProps> = ({ date, level, action, children }) => {
  const { clusterId } = useRouteParams();
  const { job } = useContext(Context);
  const { kill } = useActions(clusterId);
  const { palette } = useTheme();

  const [collapsed, setCollapsed] = useState(true);

  const handleDetailsButtonClick = useCallback(() => {
    setCollapsed(false);
  }, [setCollapsed]);
  const handleKillClick = useCallback((event: SyntheticEvent) => {
    kill(job).onClick(event, job);
  }, [kill, job]);

  const icon = useMemo(() => {
    if (level === 'WARNING') {
      return <Warning fontSize="small" htmlColor={palette.warning.main}/>;
    } else { // 'INFO' by default
      return <Info fontSize="small" htmlColor={palette.info.main}/>;
    }
  }, [level, palette]);
  const actionButton = useMemo(() => {
    if (action === 'KillJob') {
      return <Button size="small" color="secondary" onClick={handleKillClick}>Kill</Button>;
    }
  }, [action, handleKillClick]);

  const paperStyle = usePaperStyle(collapsed);
  const typographyStyle = useTypographyStyle(collapsed);

  if (collapsed) {
    return (
      <Paper variant="outlined" classes={paperStyle}>
        {icon}
        <Typography
          variant="body2"
          component={Box}
          width="0px"
          flex={1}
          paddingLeft={1}
          classes={typographyStyle}
        >
          {children}
        </Typography>
        <Button size="small" onClick={handleDetailsButtonClick}>Details</Button>
      </Paper>
    );
  } else {
    return (
      <Paper variant="outlined" classes={paperStyle}>
        <Box display="flex" alignItems="flex-start">
          {icon}
          <Typography
            variant="body2"
            component={Box}
            width="0px"
            flex={1}
            paddingLeft={1}
            classes={typographyStyle}
          >
            {children}
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" justifyContent="space-between" paddingTop={1}>
          <Typography
            variant="caption"
          >
            {formatDateDistance(date)}
          </Typography>
          {actionButton}
        </Box>
      </Paper>
    );
  }
}

const Insight: FunctionComponent = () => {
  const { job } = useContext(Context);

  const date = useMemo<Date>(() => {
    const timestamp = get(job, ['insight', 'timestamp'], NaN);
    return new Date(timestamp * 1000);
  }, [job]);
  const diagnostics = useMemo<any[]>(() => {
    return get(job, ['insight', 'diagnostics'], []);
  }, [job]);

  return (
    <>
      {
        diagnostics.map(([level, text, action]: [string, string, string], index) => (
          <Diagnostic key={index} date={date} level={level} action={action}>{text}</Diagnostic>
        ))
      }
    </>
  );
}

export default Insight;
