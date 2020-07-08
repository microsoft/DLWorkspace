import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'

import { useParams } from 'react-router-dom'

import {
  Dialog,
  DialogTitle,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Radio
} from '@material-ui/core'
import { LowPriority } from '@material-ui/icons'

import { useSnackbar } from 'notistack'

import useFetch from 'use-http-1'

import TeamContext from '../../../contexts/Team'

import SettingItem from './SettingItem'
import Context from './Context'

const SchedulingPolicyItem: FunctionComponent<{ value: 'RF' | 'FIFO' | undefined }> = ({ value }) => {
  const rfDetails = 'Runnable job first. Large jobs may be starved by small jobs.'
  const fifoDetails = 'First-in, first-out, based on job queue time.'

  const { clusterId } = useParams()
  const { enqueueSnackbar } = useSnackbar()
  const { getMeta } = useContext(Context)
  const { currentTeamId } = useContext(TeamContext)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogValue, setDialogValue] = useState<'RF' | 'FIFO'>()

  const getText = useCallback((value: 'RF' | 'FIFO' | undefined) => {
    if (value === undefined) return undefined
    if (value === 'FIFO') return `FIFO: ${fifoDetails}`
    return `RF: ${rfDetails}`
  }, [])
  const text = useMemo(() => getText(value), [getText, value])

  const { response, error, patch } = useFetch(`/api/v2/clusters/${clusterId}/teams/${currentTeamId}/meta`, {
    headers: {
      'Content-Type': 'application/json'
    }
  })

  const handleItemConfigure = useCallback(() => {
    setDialogOpen(true)
    setDialogValue(value === 'FIFO' ? 'FIFO' : 'RF')
  }, [setDialogOpen, setDialogValue, value])
  const handleDialogCancel = useCallback(() => {
    setDialogOpen(false)
  }, [setDialogOpen])
  const handleDialogItemClick = useCallback((itemValue: 'RF' | 'FIFO') => () => {
    if (value !== itemValue) {
      setDialogValue(itemValue)
      setDialogOpen(false)
      patch({
        schedulingPolicy: itemValue
      }).then(() => {
        if (response.ok) {
          setDialogOpen(false)
          getMeta()
        }
      })
    }
  }, [value, patch, response, getMeta])

  useEffect(() => {
    if (error) {
      enqueueSnackbar(`Failed to set interactive GPU: ${error.message}`, { variant: 'error' })
    }
  }, [error, enqueueSnackbar])

  return (
    <>
      <SettingItem
        Icon={LowPriority}
        name="Scheduling Policy"
        text={text}
        onConfigure={handleItemConfigure}
      />
      <Dialog open={dialogOpen} onClose={handleDialogCancel}>
        <DialogTitle>Scheduling Policy</DialogTitle>
        <List disablePadding dense>
          <ListItem button onClick={handleDialogItemClick('RF')}>
            <ListItemIcon>
              <Radio checked={dialogValue === 'RF'}/>
            </ListItemIcon>
            <ListItemText primary="RF" secondary={rfDetails}/>
          </ListItem>
          <ListItem button onClick={handleDialogItemClick('FIFO')}>
            <ListItemIcon>
              <Radio checked={dialogValue === 'FIFO'}/>
            </ListItemIcon>
            <ListItemText primary="FIFO" secondary={fifoDetails}/>
          </ListItem>
        </List>
      </Dialog>
    </>
  )
}

export default SchedulingPolicyItem
