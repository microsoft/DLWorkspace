import * as React from 'react'
import {
  FunctionComponent,
  useEffect,
  useMemo
} from 'react'

import { groupBy } from 'lodash'

import useFetch from 'use-http-1'

import {
  Box,
  Grid
} from '@material-ui/core'

import { useSnackbar } from 'notistack'

import Loading from '../../../../components/Loading'

import useRouteParams from '../../useRouteParams'

import App from './App'

const Apps: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams()
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { data, loading, error, get } = useFetch(
    `/api/clusters/${clusterId}/jobs/${jobId}/endpoints`, [clusterId, jobId])

  const { ipython, tensorboard, theia, port } = useMemo(() => {
    if (!Array.isArray(data)) return {} as const
    return groupBy(data, (endpoint) => {
      if (endpoint['name'] === 'ssh') return 'ssh'
      if (endpoint['name'] === 'ipython') return 'ipython'
      if (endpoint['name'] === 'tensorboard') return 'tensorboard'
      if (endpoint['name'] === 'theia') return 'theia'
      return 'port'
    })
  }, [data])

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

  if (data === undefined) {
    return <Loading>Fetching App Status</Loading>
  }

  return (
    <Box padding={3}>
      <Grid container spacing={3}>
        {
          ipython !== undefined
            ? ipython.map(endpoint => <App key={endpoint['id']} name="ipython" endpoint={endpoint}/>)
            : <App key="new-ipython" name="ipython"/>
        }
        {
          tensorboard !== undefined
            ? tensorboard.map(endpoint => <App key={endpoint['id']} name="tensorboard" endpoint={endpoint}/>)
            : <App key="new-tensorboard" name="tensorboard"/>
        }
        {
          theia !== undefined
            ? theia.map(endpoint => <App key={endpoint['id']} name="theia" endpoint={endpoint}/>)
            : <App key="new-theia" name="theia"/>
        }
        {
          port !== undefined
            ? port.map(endpoint => <App key={endpoint['id']} endpoint={endpoint}/>)
            : null
        }
        <App key="new-port"/>
      </Grid>
    </Box>
  )
}

Apps.displayName = 'Apps'

export default Apps
