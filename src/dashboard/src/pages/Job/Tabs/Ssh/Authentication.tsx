import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'

import { Link } from 'react-router-dom'

import useFetch from 'use-http-1'

import {
  Button,
  CircularProgress,
  ExpansionPanel,
  ExpansionPanelSummary,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Switch,
  Typography
} from '@material-ui/core'
import {
  ExpandMore,
  VpnKey
} from '@material-ui/icons'

import { useSnackbar } from 'notistack'

import useUserDialog from '../../../../hooks/useUserDialog'
import { formatDateDistance } from '../../../../utils/formats'
import Context from '../../Context'

const useKeys = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { data, error, get } = useFetch('/api/keys', [])

  const handleRetry = useCallback(() => { get() }, [get])

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar('Failed to fetch app status', {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={handleRetry}>Retry</Button>
      })
      if (key !== null) {
        return () => { closeSnackbar(key) }
      }
    }
  }, [error, enqueueSnackbar, handleRetry, closeSnackbar])

  return data
}

interface KeysProps {
  onAddKeyToCommand?: (key?: string) => void
}

const Authentication: FunctionComponent<KeysProps> = ({ onAddKeyToCommand }) => {
  const { open: openUserDialog } = useUserDialog()
  const { cluster, job } = useContext(Context)

  const keys = useKeys()

  const [addKeyToCommand, setAddKeyToCommand] = useState(false)

  const enabledKeys = useMemo(() => {
    if (keys === undefined) return undefined
    const jobTimestamp = Date.parse(job.jobTime)
    return keys.filter(
      ({ added }: { added: string }) => Date.parse(added) <= jobTimestamp)
  }, [keys, job.jobTime])

  const sambaCommandKey = useMemo(() => {
    const workStorage: string = cluster['workStorage'].replace(/^file:/, '')
    const userName: string = job['userName'].split('@', 1)[0]
    return `${workStorage}/${userName}/.ssh/id_rsa`
  }, [cluster, job])

  const handleSambaKeyClick = useCallback(() => {
    setAddKeyToCommand(value => !value)
  }, [setAddKeyToCommand])
  const handleSambaKeySwitchChange = useCallback((event: unknown, checked: boolean) => {
    setAddKeyToCommand(checked)
  }, [setAddKeyToCommand])

  useEffect(() => {
    if (onAddKeyToCommand !== undefined) {
      onAddKeyToCommand(addKeyToCommand ? sambaCommandKey : undefined)
    }
  }, [onAddKeyToCommand, addKeyToCommand, sambaCommandKey])

  return (
    <ExpansionPanel disabled={enabledKeys == null} variant="outlined">
      <ExpansionPanelSummary
        expandIcon={enabledKeys == null ? <CircularProgress size="1rem"/> : <ExpandMore/>}
      >
        <VpnKey fontSize="small"/>
        <Typography variant="subtitle2">
          &nbsp;Authentication
        </Typography>
      </ExpansionPanelSummary>
      <List dense disablePadding>
        {enabledKeys != null && enabledKeys.map((key: any) => {
          const id: string = key['id']
          const name: string = key['name']
          const added: string = key['added']
          return (
            <ListItem key={id}>
              <ListItemText
                primary={`Use the private key "${name}"`}
                secondary={`added ${formatDateDistance(new Date(added))}`}
              />
            </ListItem>
          )
        })}
        <ListItem button component={Link} to="/keys">
          <ListItemText
            primary="(Add new SSH public keys)"
            secondary="Note: will be able to use in newer sumitted jobs"
          />
        </ListItem>
        <ListItem button onClick={openUserDialog}>
          <ListItemText
            primary="Use password"
            secondary="click to see the password"
          />
        </ListItem>
        <ListItem button onClick={handleSambaKeyClick}>
          <ListItemText
            primary="(Deprecated) Use the private key in Samba"
            secondary="click to insert the private key to commands"
          />
          <ListItemSecondaryAction>
            <Switch edge="end" checked={addKeyToCommand} onChange={handleSambaKeySwitchChange}/>
          </ListItemSecondaryAction>
        </ListItem>
      </List>
    </ExpansionPanel>
  )
}

export default Authentication
