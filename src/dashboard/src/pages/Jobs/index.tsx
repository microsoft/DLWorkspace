import * as React from 'react'
import { useEffect, useState } from 'react'
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useMemo
} from 'react'
import {
  useHistory,
  useLocation,
  useParams
} from 'react-router-dom'
import {
  Container,
  FormControl,
  Grid,
  InputLabel,
  Link,
  Paper,
  Tabs,
  Tab,
  Tooltip,
  Toolbar
} from '@material-ui/core'
import SwipeableViews from 'react-swipeable-views'

import ClustersContext from '../../contexts/Clusters'
import ClusterSelector from '../../components/ClusterSelector'

import useFetch from 'use-http'
import { Info } from '@material-ui/icons'
import { withStyles } from '@material-ui/core/styles'
import Loading from '../../components/Loading'
import useHashTab from '../../hooks/useHashTab'
import ClusterContext from './ClusterContext'
import MyJobs from './MyJobs'
import AllJobs from './AllJobs'

interface RouteParams {
  clusterId: string
}

const TabView: FunctionComponent = () => {
  const [index, setIndex] = useHashTab('my', 'all')
  const onChange = useCallback((event: ChangeEvent<{}>, value: any) => {
    setIndex(value as number)
  }, [setIndex])
  const onChangeIndex = useCallback((index: number, prevIndex: number) => {
    setIndex(index)
  }, [setIndex])
  return (
    <>
      <Tabs
        value={index}
        onChange={onChange}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab label="My Jobs"/>
        <Tab label="All Jobs"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={onChangeIndex}
      >
        {index === 0 ? <MyJobs/> : <div/>}
        {index === 1 ? <AllJobs/> : <div/>}
      </SwipeableViews>
    </>
  )
}

const ClusterJobs: FunctionComponent<{ cluster: any }> = ({ cluster }) => {
  return (
    <ClusterContext.Provider value={{ cluster: cluster }}>
      <Paper elevation={2}>
        <TabView/>
      </Paper>
    </ClusterContext.Provider>
  )
}

const Jobs: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext)

  const history = useHistory()
  const { hash } = useLocation()
  const { clusterId } = useParams<RouteParams>()
  const [amlUrl, setAmlUrl ] = useState('');
  const fetchAmlUrl = '/api/clusters'
  const requestAmlUrl = useFetch(fetchAmlUrl)
  const fetchAml = async () => {
    for (var i in clusters) {
      const { amlPortal } = await requestAmlUrl.get(`/${clusters[i].id}`)
      if (amlPortal != null && amlPortal != '') {
        setAmlUrl(amlPortal)
      }
    }
  }
  useEffect(() => {
    fetchAml()
  }, [])

  const cluster = useMemo(() => {
    return clusters.filter(cluster => cluster.id === clusterId)[0]
  }, [clusters, clusterId])

  const onClusterChange = useCallback((cluster: any) => {
    // Use absolute pathname to support both
    // - Autofill at the beginning (/jobs -> /jobs/Default-Cluster/)
    // - Select Switching (/jobs/Default-Cluster/ -> /jobs/Other-Cluster/)
    const pathname = `/jobs/${cluster.id}/`
    history.replace({ pathname, hash })
  }, [history, hash])

  return (
    <Container fixed maxWidth="xl">
      <Toolbar disableGutters>
        <FormControl fullWidth>
          { amlUrl != '' ? 
          <Grid item xs={12} container justify="flex-end">
            <Info fontSize="small" color="primary"/>
            <Tooltip title="New experimental features. Global job scheduler enables running job on underutilized GPU capacity from other teams. Elastic training enables running a training job in a fault-tolernat and elastic manner.">
              <Link href={amlUrl} target="_blank" underline='none'>Try global job scheduler and elastic training</Link>
            </Tooltip>
          </Grid>: null}
          <InputLabel>Choose Cluster</InputLabel>
          <ClusterSelector defaultId={clusterId} onChange={onClusterChange}/>
        </FormControl>
      </Toolbar>
      {
        cluster !== undefined
          ? <ClusterJobs key={cluster.id} cluster={cluster}/>
          : <Loading/>
      }
    </Container>
  )
}

export default Jobs
