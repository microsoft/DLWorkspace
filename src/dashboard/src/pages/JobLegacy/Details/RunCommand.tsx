import * as React from 'react'
import { useState, useCallback, useContext } from 'react'

import {
  IconButton,
  InputAdornment,
  TextField,
} from '@material-ui/core'
import { DirectionsRun } from '@material-ui/icons'

import useFetch from 'use-http'

import Context from './Context'

const RunCommand: React.FC = () => {
  const { clusterId, jobId } = useContext(Context)
  const { post } = useFetch(`/api/clusters/${clusterId}/jobs/${jobId}/commands`)
  // const [commands] = get();

  const [command, setCommand] = useState('')
  const onCommandChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setCommand(event.target.value)
  }, [setCommand])

  const runCommand = useCallback(() => {
    post({ command })
  }, [command])

  return (
    <TextField
      fullWidth
      variant="outlined"
      label="Run Command"
      value={command}
      onChange={onCommandChange}
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <IconButton edge="end" onClick={runCommand}>
              <DirectionsRun/>
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  )
}

export default RunCommand
