import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef
} from 'react'

import {
  CardContent,
  IconButton,
  InputAdornment,
  TextField,
  Tooltip
} from '@material-ui/core'
import {
  FileCopyRounded
} from '@material-ui/icons'

import copy from 'clipboard-copy'
import { useSnackbar } from 'notistack'

import UserContext from '../../../contexts/User'
import { useCluster } from './Context'

interface CopyableTextFieldProps {
  label: string
  value: string
}

const CopyableTextField: FunctionComponent<CopyableTextFieldProps> = ({ label, value }) => {
  const { enqueueSnackbar } = useSnackbar()
  const input = useRef<HTMLInputElement>()
  const handleMouseOver = useCallback(() => {
    if (input.current) {
      input.current.select()
    }
  }, [input])
  const handleClick = React.useCallback(() => {
    copy(value)
    enqueueSnackbar('Successfully copied', { variant: 'success' })
  }, [value, enqueueSnackbar])
  return (
    <TextField
      inputRef={input}
      label={label}
      value={value}
      multiline
      rows={2}
      fullWidth
      variant="outlined"
      margin="dense"
      InputProps={{
        readOnly: true,
        endAdornment: (
          <InputAdornment position="end">
            <Tooltip title="Copy" placement="right">
              <IconButton onClick={handleClick}>
                <FileCopyRounded/>
              </IconButton>
            </Tooltip>
          </InputAdornment>
        )
      }}
      onMouseOver={handleMouseOver}
    />
  )
}

const DirectoryContent: FunctionComponent = () => {
  const { email } = useContext(UserContext)
  const { status } = useCluster()
  const workStorage = useMemo(() => {
    if (email == null) return ''
    if (status == null) return ''
    if (status.config == null) return ''
    return status.config.workStorage + '/' + email.split('@', 1)[0]
  }, [email, status])
  const dataStorage = useMemo(() => {
    if (status == null) return ''
    if (status.config == null) return ''
    return status.config.dataStorage
  }, [status])
  return (
    <CardContent>
      <CopyableTextField
        label="Work Directory"
        value={workStorage}
      />
      <CopyableTextField
        label="Data Directory"
        value={dataStorage}
      />
    </CardContent>
  )
}

export default DirectoryContent
