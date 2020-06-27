import * as React from 'react';
import {
  FunctionComponent,
  memo,
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

const useMessagePaperStyle = makeStyles(theme => createStyles({
  root: {
    display: 'flex',
    flexDirection: (expanded: boolean) => expanded ? 'column' : 'row',
    alignItems: (expanded: boolean) => expanded ? 'stretch' : 'center',
    marginBottom: theme.spacing(1),
    padding: theme.spacing(1),
  },
}));

const LevelIcon: FunctionComponent<{ children: string }> = memo(({ children }) => {
  const { palette } = useTheme();

  if (children === 'WARNING') {
    return <Warning fontSize="small" htmlColor={palette.warning.main}/>;
  } else { // 'INFO' by default
    return <Info fontSize="small" htmlColor={palette.info.main}/>;
  }
}, ({ children: prevChildren }, { children: nextChildren }) => prevChildren === nextChildren);

const ActionButton: FunctionComponent<{ children: string }> = ({ children }) => {
  const { clusterId } = useRouteParams();
  const { job } = useContext(Context);
  const { pause, kill } = useActions(clusterId);

  const handlePauseButtonClick = useCallback((event: unknown) => {
    pause(job).onClick(event, job);
  }, [pause, job]);
  const handleKillButtonClick = useCallback((event: unknown) => {
    kill(job).onClick(event, job);
  }, [kill, job]);

  if (/^https?:\/\//.test(children)) {
    return <Button size="small" color="primary" href={children} target="_blank" rel="noopener noreferrer">Link</Button>
  }
  if (children === 'PauseJob') {
    return <Button size="small" color="primary" onClick={handlePauseButtonClick}>Pause</Button>
  }
  if (children === 'KillJob') {
    return <Button size="small" color="secondary" onClick={handleKillButtonClick}>Kill</Button>
  }
  return null;
};

interface CollapsedMessageProps {
  level: string;
  count: number;
  onExpand(): void;
  children: string;
}

const CollapsedMessage: FunctionComponent<CollapsedMessageProps> = ({ level, count, onExpand, children }) => {
  const paperStyle = useMessagePaperStyle(false);
  return (
    <Paper variant="outlined" classes={paperStyle}>
      <LevelIcon>{level}</LevelIcon>
      <Typography
        variant="body2"
        noWrap
        component={Box}
        width="0px"
        flex={1}
        paddingLeft={1}
        overflow="hidden"
        textOverflow="ellipsis"
      >
        {children}
      </Typography>
      { count > 1 && (
        <Typography variant="body2" component={Box} paddingRight={1}>
          {`and ${count - 1} more`}
        </Typography>
      ) }
      <Button size="small" color="primary" onClick={onExpand}>Expand</Button>
    </Paper>
  );
};

interface MessageProps {
  date: Date;
  level: string;
  action: string;
  children: string;
}

const Message: FunctionComponent<MessageProps> = ({ date, level, action, children }) => {
  const paperStyle = useMessagePaperStyle(true);
  return (
    <Paper variant="outlined" classes={paperStyle}>
      <Box display="flex" alignItems="flex-start">
        <LevelIcon>{level}</LevelIcon>
        <Typography
          variant="body2"
          component={Box}
          width="0px"
          flex={1}
          paddingLeft={1}
        >
          {children}
        </Typography>
      </Box>
      <Box display="flex" alignItems="flex-end" justifyContent="space-between" paddingTop={1}>
        <Typography variant="caption">{formatDateDistance(date)}</Typography>
        <ActionButton>{action}</ActionButton>
      </Box>
    </Paper>
  );
};

const Insight: FunctionComponent = () => {
  const { job } = useContext(Context);

  const [collapsed, setCollapsed] = useState(true);

  const date = useMemo<Date>(() => {
    const timestamp = get(job, ['insight', 'timestamp'], NaN);
    return new Date(timestamp * 1000);
  }, [job]);
  const diagnostics = useMemo<any[]>(() => {
    return get(job, ['insight', 'diagnostics'], []);
  }, [job]);

  const handleExpand = useCallback(() => {
    setCollapsed(false);
  }, [setCollapsed]);

  if (diagnostics.length === 0) {
    return null;
  }
  if (collapsed) {
    const [level, text] = diagnostics[0];
    return (
      <CollapsedMessage
        level={level}
        count={diagnostics.length}
        onExpand={handleExpand}
      >
        {text}
      </CollapsedMessage>
    );
  }
  return (
    <>
      {
        diagnostics.map(([level, text, action]: [string, string, string], index) => (
          <Message key={index} date={date} level={level} action={action}>{text}</Message>
        ))
      }
    </>
  );
}

export default Insight;
