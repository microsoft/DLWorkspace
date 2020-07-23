import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useEffect,
  useMemo
} from 'react'

import useFetch from 'use-http-1'

import {
  Box,
  Button,
  CircularProgress,
  ExpansionPanel,
  ExpansionPanelSummary,
  ExpansionPanelDetails,
  ExpansionPanelActions,
  Typography
} from '@material-ui/core'
import {
  ExpandMore,
  NetworkCheck
} from '@material-ui/icons'

import { useSnackbar } from 'notistack'

import useRouteParams from '../../useRouteParams'

const useAllowedIp = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { clusterId } = useRouteParams()
  const { data, error, get } = useFetch(`/api/clusters/${clusterId}/allowed-ip`, [clusterId])
  const { put } = useFetch(`/api/clusters/${clusterId}/allowed-ip`)

  const handleRetry = useCallback(() => { get() }, [get])
  const handleUpdate = useCallback((ip: string) => {
    enqueueSnackbar('Updating allowed IP', { variant: 'info' })
    put({ ip }).then(() => {
      return get()
    }).then(() => {
      enqueueSnackbar('Successfully updated allowed IP', { variant: 'success' })
    }, () => {
      enqueueSnackbar('Failed to update allowed IP', { variant: 'error' })
    })
  }, [put, get, enqueueSnackbar])

  useEffect(() => {
    if (error !== undefined && error.name !== '404') {
      const key = enqueueSnackbar('Failed to fetch allowed ip', {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={handleRetry}>Retry</Button>
      })
      if (key !== null) {
        return () => { closeSnackbar(key) }
      }
    }
  }, [error, enqueueSnackbar, handleRetry, closeSnackbar])

  if (error !== undefined && error.name === '404') {
    return [null, handleUpdate] as const
  }
  if (data !== undefined) {
    return [data['ip'] as string, handleUpdate] as const
  }
  return [undefined, handleUpdate] as const
}

const useMyIp = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { data, error, get } = useFetch('https://httpbin.org/ip', [])

  const handleRetry = useCallback(() => { get() }, [get])

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar('Failed to fetch your ip', {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={handleRetry}>Retry</Button>
      })
      if (key !== null) {
        return () => { closeSnackbar(key) }
      }
    }
  }, [error, enqueueSnackbar, handleRetry, closeSnackbar])

  return data === undefined ? undefined : data['origin']
}

const Network: FunctionComponent = () => {
  const [allowedIp, setAllowedIp] = useAllowedIp()
  const myIp = useMyIp()

  const needUpdate = useMemo(() => {
    if (allowedIp === undefined) return undefined
    if (myIp === undefined) return undefined
    return allowedIp !== myIp
  }, [allowedIp, myIp])

  const handleUpdate = useCallback(() => {
    if (myIp !== undefined) {
      setAllowedIp(myIp)
    }
  }, [setAllowedIp, myIp])

  return (
    <ExpansionPanel disabled={allowedIp === undefined || myIp === undefined} variant="outlined">
      <ExpansionPanelSummary
        expandIcon={
          allowedIp === undefined || myIp === undefined
            ? <CircularProgress size="1rem"/>
            : <ExpandMore/>
        }
      >
        <NetworkCheck fontSize="small"/>
        <Typography variant="subtitle2">
          &nbsp;Network
        </Typography>
      </ExpansionPanelSummary>
      <ExpansionPanelDetails>
        <Box>
          {
            allowedIp !== undefined && (
              <Typography component="div">
                {
                  allowedIp !== null ? (
                    <>
                      Your allowed IP is:&nbsp;
                      <Typography display="inline" color="primary">
                        {allowedIp}
                      </Typography>
                    </>
                  ) : (
                    <>
                      You have no allowed IP in this cluster
                    </>
                  )
                }
              </Typography>
            )
          }
          {
            myIp !== undefined && (
              <Typography component="div">
                Your current IP is:&nbsp;
                <Typography display="inline" color={myIp !== allowedIp ? 'secondary' : 'primary'}>
                  {myIp}
                </Typography>
              </Typography>
            )
          }
          {
            needUpdate === true && (
              <Typography variant="body2">
                Try updating your allowed IP with your current IP if you meet network issues.
              </Typography>
            )
          }
        </Box>
      </ExpansionPanelDetails>
      { needUpdate === true && (
        <ExpansionPanelActions>
          <Button color="primary" onClick={handleUpdate}>Update</Button>
        </ExpansionPanelActions>
      ) }
    </ExpansionPanel>
  )
}

export default Network
