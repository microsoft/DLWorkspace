import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'

import useFetch from 'use-http-1'

import {
  Box,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction
} from '@material-ui/core'
import {
  FileCopy
} from '@material-ui/icons'

import { useSnackbar } from 'notistack'

import copy from 'clipboard-copy'

import Loading from '../../../../components/Loading'

import Context from '../../Context'
import useRouteParams from '../../useRouteParams'

import Authentication from './Authentication'
import Network from './Network'

const ROLE_ORDER: { [roleName: string]: number } = {
  'master': 0,
  'ps': 1,
  'worker': 2
}

const useEndpoints = () => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { data, loading, error, get } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/endpoints`, [clusterId, jobId])
  const { response, post } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/endpoints`, [clusterId, jobId])

  const handleEnable = useCallback(() => {
    post({ endpoints: ['ssh'] }).then(() => {
      if (response.ok) {
        enqueueSnackbar('Enabling SSH', { variant: 'info' })
      } else {
        return response.text().then(text => Promise.reject(Error(text)))
      }
    }).catch((error) => {
      const message = error != null && error.message != null
        ? `Failed to enable SSH: ${String(error.message)}`
        : 'Failed to enable SSH'
      enqueueSnackbar(message, { variant: 'error' })
    })
  }, [post, response, enqueueSnackbar])

  useEffect(() => {
    if (!loading) {
      const timeout = window.setTimeout(get, 3000)
      return () => { clearTimeout(timeout) }
    }
  }, [loading, get])

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar('Failed to fetch app status', {
        variant: 'error',
        persist: true
      })
      if (key !== null) {
        return () => { closeSnackbar(key) }
      }
    }
  }, [error, enqueueSnackbar, closeSnackbar])

  return [data, handleEnable] as const
}

const Ssh: FunctionComponent = () => {
  const { enqueueSnackbar } = useSnackbar()
  const { cluster, job, owned } = useContext(Context)

  const [endpoints, enableSSH] = useEndpoints()

  const [commandKey, setCommandKey] = useState<string>()

  const sshEndpoints = useMemo(() => {
    if (endpoints == null) return undefined
    return endpoints.filter(
      ({ name }: { name: string }) => name === 'ssh'
    ).sort(
      (a: any, b: any) => {
        const aRoleName = a['role-name']
        const bRoleName = b['role-name']
        const aRoleOrder = aRoleName in ROLE_ORDER ? ROLE_ORDER[aRoleName] : Infinity
        const bRoleOrder = bRoleName in ROLE_ORDER ? ROLE_ORDER[bRoleName] : Infinity
        if (aRoleOrder !== bRoleOrder) {
          return aRoleOrder - bRoleOrder
        }
        const aRoleIndex = a['role-idx']
        const bRoleIndex = b['role-idx']
        return Number(aRoleIndex) - Number(bRoleIndex)
      }
    )
  }, [endpoints])
  const userName = useMemo(() => {
    return (job['userName'] as string).split('@', 1)[0]
  }, [job])

  const handleEnableClick = useCallback(() => {
    enableSSH()
  }, [enableSSH])
  const handleAddKeyToCommand = useCallback(setCommandKey, [setCommandKey])
  const handleListItemClick = useCallback((content: string) => () => {
    copy(content).then(() => {
      enqueueSnackbar('Copied to clipboard', { variant: 'info' })
    }, () => {
      enqueueSnackbar('Failed to copy to clipboard', { variant: 'error' })
    })
  }, [enqueueSnackbar])

  if (sshEndpoints === undefined) {
    return <Loading>Fetching SSH info</Loading>
  }

  if (sshEndpoints.length === 0) {
    return (
      <Box padding={3} display="flex" justifyContent="center">
        <Button
          color="primary"
          size="large"
          onClick={handleEnableClick}
        >
          Enable SSH
        </Button>
      </Box>
    )
  }

  return <>
    <List disablePadding>
      {sshEndpoints.map((endpoint: any) => {
        const id: string = endpoint['id']
        const roleName: string = endpoint['role-name']
        const roleIndex: string = endpoint['role-idx']
        const nodeName: string = endpoint['nodeName']
        const domain: string = endpoint['domain']
        const port: string = endpoint['port']
        const status: string = endpoint['status']
        const role = `${roleName} ${roleIndex}`
        const host = `${nodeName}.${domain}`
        const command = commandKey !== undefined
          ? `ssh -i ${commandKey} -p ${port} ${userName}@${host}`
          : `ssh -p ${port} ${userName}@${host}`
        if (status === 'running') {
          return (
            <ListItem key={id} button onClick={handleListItemClick(command)}>
              <ListItemText
                primary={role}
                secondary={command}
              />
              <ListItemSecondaryAction>
                <IconButton onClick={handleListItemClick(command)}>
                  <FileCopy/>
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          )
        } else {
          return (
            <ListItem key={id}>
              <ListItemText
                primary={role}
                secondary={status}
              />
            </ListItem>
          )
        }
      })}
    </List>
    <Box paddingX={2} paddingBottom={2}>
      { owned && <Authentication onAddKeyToCommand={handleAddKeyToCommand}/> }
      { owned && cluster.supportAllowedIp === true && <Network/> }
    </Box>
  </>
}

Ssh.displayName = 'SSH'

export default Ssh
