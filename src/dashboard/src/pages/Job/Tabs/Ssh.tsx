import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useEffect
} from 'react'

import useFetch from 'use-http-1'

import {
  Button
} from '@material-ui/core'

import { useSnackbar } from 'notistack'

import useRouteParams from '../useRouteParams'

const useEndpoints = () => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { data, loading, error, get } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/endpoints`, [clusterId, jobId])

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

  return data
}

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

const Ssh: FunctionComponent = () => {
  const endpoints = useEndpoints()
  const keys = useKeys()
  return <>
    <pre>{JSON.stringify(endpoints, null, 2)}</pre>
    <pre>{JSON.stringify(keys, null, 2)}</pre>
  </>
}

Ssh.displayName = 'SSH'

export default Ssh
