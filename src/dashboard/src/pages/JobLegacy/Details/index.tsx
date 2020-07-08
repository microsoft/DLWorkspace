import * as React from 'react'
import { Fragment, useEffect, useState } from 'react'
import {
  Theme,
  useTheme,
  Box,
  Tab,
  Tabs,
  makeStyles,
  createStyles,
  AppBar,
  Container,
  CircularProgress,
  useMediaQuery, Snackbar, SnackbarContent
} from '@material-ui/core'
import useFetch from 'use-http'

import UserContext from '../../../contexts/User'
import Context from './Context'
import Brief from './Brief'
import Log from './Log'
import Monitor from './Monitor'
import Endpoints from './Endpoints'
import { DLTSTabPanel } from '../../CommonComponents/DLTSTabPanel'
import SwipeableViews from 'react-swipeable-views'
import { DLTSTabs } from '../../CommonComponents/DLTSTabs'
import { JobDetailTitles, readOnlyJobDetailTitles } from '../../../Constants/TabsContants'
import { DLTSSnackbar } from '../../CommonComponents/DLTSSnackbar'
import ClusterContext from '../../../contexts/Clusters'
import TeamContext from '../../../contexts/Team'
import { useTimeoutFn } from 'react-use'
interface Props {
  team: string
  clusterId: string
  jobId: string
  job: any
}

const JobDetails: React.FC<Props> = ({ clusterId, jobId, job, team }) => {
  const { email } = React.useContext(UserContext)
  const { data: cluster } = useFetch(`/api/clusters/${clusterId}`, { onMount: true })
  const [value, setValue] = React.useState(0)
  const theme = useTheme()
  const [showIframe, setShowIframe] = useState(false)
  const [refresh, setRefresh] = React.useState(window.navigator.userAgent.indexOf('Edge') == -1)
  const handleChangeIndex = (index: number) => {
    setShowIframe(false)
    if (window.navigator.userAgent.indexOf('Edge') != -1) {
      setTimeout(() => {
        setShowIframe(true)
        setRefresh(true)
      }, 2000)
    }
    setValue(index)
  }
  const { clusters } = React.useContext(ClusterContext)
  const [isReady, reset, cancel] = useTimeoutFn(() => {
    setRefresh(true)
    setShowIframe(true)
  }, 2000)
  const isReadOnly = !(clusters.filter((cluster: any) => cluster.id === clusterId)[0].admin || email === job['userName'])
  useEffect(() => {
    if (isReady()) {
      reset()
    }
    return () => {
      cancel()
    }
  }, [])
  const isDesktop = useMediaQuery(theme.breakpoints.up('sm'))
  const [showOpen, setshowOpen] = useState(false)
  const handleWarnClose = () => {
    setshowOpen(false)
  }

  if (isReadOnly) {
    return (
      <Context.Provider value={{ jobId, clusterId, job, cluster }}>
        <DLTSTabs value={value} setValue={setValue} titles={readOnlyJobDetailTitles} setRefresh={setRefresh} />
        <SwipeableViews
          axis={theme.direction === 'rtl' ? 'x-reverse' : 'x'}
          index={value}
          onChangeIndex={handleChangeIndex}
        >
          <DLTSTabPanel value={value} index={0} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Brief readonly/></Container>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={1} dir={theme.direction}>
            { refresh ? cluster && <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Monitor/></Container> : <CircularProgress/>}
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={2} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Log/></Container>
          </DLTSTabPanel>
        </SwipeableViews>

      </Context.Provider>
    )
  } else {
    return (
      <Context.Provider value={{ jobId, clusterId, job, cluster }}>
        <DLTSTabs value={value} setValue={setValue} titles={JobDetailTitles} setRefresh={setRefresh} />
        <SwipeableViews
          axis={theme.direction === 'rtl' ? 'x-reverse' : 'x'}
          index={value}
          onChangeIndex={handleChangeIndex}
        >
          <DLTSTabPanel value={value} index={0} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Brief/></Container>
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={1} dir={theme.direction}>
            { refresh ? (job['jobStatus'] !== 'pausing' && job['jobStatus'] !== 'paused') && <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Endpoints setOpen={setshowOpen} status={job['jobStatus']}/></Container> : <CircularProgress/>}
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={2} dir={theme.direction}>
            { showIframe ? cluster && <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Monitor/></Container> : <CircularProgress/>}
          </DLTSTabPanel>
          <DLTSTabPanel value={value} index={3} dir={theme.direction}>
            <Container maxWidth={isDesktop ? 'lg' : 'xs'} ><Log/></Container>
          </DLTSTabPanel>
        </SwipeableViews>
        <DLTSSnackbar message={'Copied'}
          open={showOpen}
          handleWarnClose={handleWarnClose}
          autoHideDuration={500}
        />
      </Context.Provider>
    )
  }
}

export default JobDetails
