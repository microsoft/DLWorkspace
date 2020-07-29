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
            ? ipython.map((endpoint, index) => <App key={`ipython-${index}`} name="ipython" endpoint={endpoint}/>)
            : <App key="ipython-0" name="ipython"/>
        }
        {
          tensorboard !== undefined
            ? tensorboard.map((endpoint, index) => <App key={`tensorboard-${index}`} name="tensorboard" endpoint={endpoint}/>)
            : <App key="tensorboard-0" name="tensorboard"/>
        }
        {
          theia !== undefined
            ? theia.map((endpoint, index) => <App key={`theia-${index}`} name="theia" endpoint={endpoint}/>)
            : <App key="theia-0" name="theia"/>
        }
        {
          port !== undefined
            ? port.map(endpoint => <App key={`port-${endpoint['id'] as string}`} endpoint={endpoint}/>)
            : null
        }
        <App key="port-new"/>
      </Grid>
    </Box>
  )
}

Apps.displayName = 'Apps'

export default Apps
