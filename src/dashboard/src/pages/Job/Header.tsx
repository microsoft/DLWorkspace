import * as React from 'react';
import {
  FunctionComponent,
  createElement,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react'

import { Link } from 'react-router-dom'

import {
  Box,
  IconButton,
  Input,
  InputAdornment,
  Toolbar,
  Typography,
  Tooltip
} from '@material-ui/core';
import {
  ArrowBack,
  Check,
  Edit
} from '@material-ui/icons'
import { useSnackbar } from 'notistack'

import useActions from '../../hooks/useActions';
import JobStatus from '../../components/JobStatus';

import useRouteParams from './useRouteParams';
import Context from './Context';

const Header: FunctionComponent<{ manageable: boolean }> = ({ manageable }) => {
  const { enqueueSnackbar } = useSnackbar()
  const { clusterId, jobId } = useRouteParams()
  const { accessible, admin, job } = useContext(Context)
  const { support, approve, kill, pause, resume, exemption } = useActions(clusterId)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>()
  const handleRenameButtonClick = useCallback(() => {
    setEditing(true)
  }, [])
  const handleCheckButtonClick = useCallback(() => {
    if (inputRef.current === undefined) return
    const name = inputRef.current.value
    if (name === '') return
    fetch(`/api/clusters/${clusterId}/jobs/${jobId}/name`, {
      method: 'PUT',
      body: JSON.stringify({ name }),
      headers: { 'Content-Type': 'application/json' }
    }).then((response) => {
      if (response.ok) {
        enqueueSnackbar('Rename successfully', { variant: 'success' })
      } else {
        throw Error()
      }
    }).catch(() => {
      enqueueSnackbar('Failed to rename', { variant: 'error' })
    }).then(() => {
      setBusy(false)
    }, () => {})
  }, [clusterId, jobId, enqueueSnackbar])

  const availableActions = useMemo(() => {
    const actions = [support];
    if (manageable && admin) actions.push(approve, exemption);
    if (manageable) actions.push(pause, resume, kill);
    return actions;
  }, [manageable, admin, support, approve, kill, pause, resume, exemption]);

  const actionButtons = availableActions.map((action, index) => {
    const { hidden, icon, tooltip, onClick } = action(job)
    if (hidden === true) return null
    return (
      <Tooltip key={index} title={tooltip as string}>
        <IconButton onClick={(event) => onClick(event, job)}>
          {createElement(icon)}
        </IconButton>
      </Tooltip>
    )
  })

  return (
    <Toolbar disableGutters variant="dense">
      {accessible && (
        <IconButton
          edge="start"
          color="inherit"
          component={Link}
          to="./"
        >
          <ArrowBack/>
        </IconButton>
      )}
      <Box width={0} flex={1} display="flex">
        { editing ? (
          <Input
            defaultValue={job['jobName']}
            disabled={busy}
            inputRef={inputRef}
            endAdornment={
              <InputAdornment position="end">
                <IconButton
                  edge="start"
                  color="inherit"
                  onClick={handleCheckButtonClick}
                >
                  <Check/>
                </IconButton>
              </InputAdornment>
            }
          />
        ) : (
          <>
            <Typography variant="h6" component={Box} flexShrink={1} overflow="hidden" whiteSpace="nowrap" textOverflow="ellipsis">
              {job['jobName']}
            </Typography>
            { manageable && (
              <Tooltip title="Rename">
                <IconButton
                  color="inherit"
                  size="small"
                  onClick={handleRenameButtonClick}
                >
                  <Edit/>
                </IconButton>
              </Tooltip>
            ) }
          </>
        ) }
        <Box flexGrow={1} paddingLeft={1}>
          <JobStatus cluster={clusterId} job={job}/>
        </Box>
      </Box>
      {actionButtons}
    </Toolbar>
  );
}

export default Header;
