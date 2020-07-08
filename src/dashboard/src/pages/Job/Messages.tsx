import * as React from 'react'
import {
  FunctionComponent,
  memo,
  useCallback,
  useContext,
  useMemo,
  useState
} from 'react'

import { get, map } from 'lodash'

import {
  Box,
  Button,
  Paper,
  Tooltip,
  Typography,
  createStyles,
  makeStyles,
  useTheme
} from '@material-ui/core'
import {
  Cancel,
  Error,
  Info,
  Warning
} from '@material-ui/icons'

import useActions from '../../hooks/useActions'
import { formatDateDistance } from '../../utils/formats'

import useRouteParams from './useRouteParams'
import Context from './Context'

const LEVELS_VALUE: { [level: string]: number } = {
  CRITICAL: 50,
  ERROR: 40,
  WARNING: 30,
  INFO: 20,
  DEBUG: 10
}

const useMessagePaperStyle = makeStyles(theme => createStyles({
  root: {
    display: 'flex',
    flexDirection: (expanded: boolean) => expanded ? 'column' : 'row',
    alignItems: (expanded: boolean) => expanded ? 'stretch' : 'center',
    marginBottom: theme.spacing(1),
    padding: theme.spacing(1)
  }
}))

const LevelIcon: FunctionComponent<{ children: string }> = memo(({ children }) => {
  const { palette } = useTheme()

  if (children === 'CRITICAL') {
    return <Cancel fontSize="small" htmlColor={palette.error.main}/>
  } else if (children === 'ERROR') {
    return <Error fontSize="small" htmlColor={palette.error.main}/>
  } else if (children === 'WARNING') {
    return <Warning fontSize="small" htmlColor={palette.warning.main}/>
  } else { // 'INFO' by default
    return <Info fontSize="small" htmlColor={palette.info.main}/>
  }
}, ({ children: prevChildren }, { children: nextChildren }) => prevChildren === nextChildren)

const ActionButton: FunctionComponent<{ children: string }> = ({ children }) => {
  const { clusterId } = useRouteParams()
  const { job } = useContext(Context)
  const { pause, kill } = useActions(clusterId)

  const handlePauseButtonClick = useCallback((event: unknown) => {
    pause(job).onClick(event, job)
  }, [pause, job])
  const handleKillButtonClick = useCallback((event: unknown) => {
    kill(job).onClick(event, job)
  }, [kill, job])

  if (/^https?:\/\//.test(children)) {
    return <Button size="small" color="primary" href={children} target="_blank" rel="noopener noreferrer">Link</Button>
  }
  if (children === 'PauseJob') {
    return <Button size="small" color="primary" onClick={handlePauseButtonClick}>Pause</Button>
  }
  if (children === 'KillJob') {
    return <Button size="small" color="secondary" onClick={handleKillButtonClick}>Kill</Button>
  }
  return null
}

interface CollapsedMessageProps {
  level: string
  count: number
  onExpand(): void
  children: string
}

const CollapsedMessage: FunctionComponent<CollapsedMessageProps> = ({ level, count, onExpand, children }) => {
  const paperStyle = useMessagePaperStyle(false)
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
        <Typography variant="body2" component={Box} paddingX={1}>
          {`and ${count - 1} more`}
        </Typography>
      ) }
      <Button size="small" color="primary" onClick={onExpand}>Show All</Button>
    </Paper>
  )
}

interface MessageProps {
  date: Date
  level: string
  action: string
  children: string
}

const Message: FunctionComponent<MessageProps> = ({ date, level, action, children }) => {
  const paperStyle = useMessagePaperStyle(true)
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
        <Tooltip title={date.toLocaleString()} placement="right">
          <Typography variant="caption">{formatDateDistance(date)}</Typography>
        </Tooltip>
        <ActionButton>{action}</ActionButton>
      </Box>
    </Paper>
  )
}

const Messages: FunctionComponent = () => {
  const { job } = useContext(Context)

  const [collapsed, setCollapsed] = useState(true)

  const diagnosticMessageProps = useMemo<MessageProps[]>(() => {
    const timestamp = get(job, ['insight', 'timestamp'], NaN)
    const date = new Date(timestamp * 1000)
    const diagnostics = get(job, ['insight', 'diagnostics'], [])

    return map(diagnostics,
      ([level, children, action]: [string, string, string]) => ({ date, level, action, children }))
  }, [job])

  const repairMessageProps = useMemo<MessageProps[]>(() => {
    const repairMessage = get(job, 'repairMessage')
    if (repairMessage == null || repairMessage.timestamp == null) return []
    const date = new Date(repairMessage.timestamp * 1000)
    const [level, children, action] = repairMessage.message
    return [{ date, level, action, children }]
  }, [job])

  const messageProps = useMemo(() =>
    diagnosticMessageProps.concat(repairMessageProps)
      .sort(({ level: levelA }, { level: levelB }) => {
        const valueA = LEVELS_VALUE[levelA] || 0
        const valueB = LEVELS_VALUE[levelB] || 0
        return valueA - valueB
      })
      .reverse(),
  [diagnosticMessageProps, repairMessageProps])

  const handleExpand = useCallback(() => {
    setCollapsed(false)
  }, [setCollapsed])

  if (messageProps.length === 0) {
    return null
  }
  if (collapsed) {
    const { level, children } = messageProps[0]
    return (
      <CollapsedMessage
        level={level}
        count={messageProps.length}
        onExpand={handleExpand}
      >
        {children}
      </CollapsedMessage>
    )
  }
  return (
    <>{ messageProps.map((props, index) => <Message key={index} {...props}/>) }</>
  )
}

export default Messages
