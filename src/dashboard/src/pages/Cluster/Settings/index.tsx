import * as React from 'react'
import {
  FunctionComponent,
  useContext,
  useEffect,
  useMemo
} from 'react'
import { find, get } from 'lodash'

import { useParams } from 'react-router-dom'

import { List } from '@material-ui/core'

import { useSnackbar } from 'notistack'

import useFetch from 'use-http-1'

import TeamContext from '../../../contexts/Team'
import ClustersContext from '../../../contexts/Clusters'

import Context from './Context'
import TimeoutItem from './TimeoutItem'
import InteractiveGpuItem from './InteractiveGpuItem'
import SchedulingPolicyItem from './SchedulingPolicyItem'

interface Props {
  data: any
}

const Settings: FunctionComponent<Props> = ({ data }) => {
  const { clusterId } = useParams()
  const { closeSnackbar, enqueueSnackbar } = useSnackbar()
  const { currentTeamId } = useContext(TeamContext)
  const { clusters } = useContext(ClustersContext)

  const admin = useMemo(() => {
    const cluster = find(clusters, ({ id }) => id === clusterId)
    return Boolean(cluster && cluster['admin'])
  }, [clusters, clusterId])

  const { data: metaData, error: metaError, get: getMeta } = useFetch(
    `/api/v2/clusters/${clusterId}/teams/${currentTeamId}/meta`,
    [clusterId, currentTeamId])

  const timeout = useMemo<number | null | undefined>(
    () => get(metaData, ['timeout']), [metaData])
  const interactiveGpu = useMemo<number | null | undefined>(
    () => get(metaData, ['interactiveGpu']), [metaData])
  const schedulingPolicy = useMemo<'RF' | 'FIFO' | undefined>(
    () => get(metaData, ['schedulingPolicy']), [metaData])

  useEffect(() => {
    if (metaError) {
      const key = enqueueSnackbar('Failed to load meta config of the team.', {
        variant: 'error',
        persist: true
      })
      if (key !== null) {
        return () => closeSnackbar(key)
      }
    }
  }, [metaError, enqueueSnackbar, closeSnackbar])

  return (
    <Context.Provider value={{ data, admin, getMeta }}>
      <List disablePadding>
        <TimeoutItem value={timeout}/>
        <InteractiveGpuItem value={interactiveGpu}/>
        <SchedulingPolicyItem value={schedulingPolicy}/>
      </List>
    </Context.Provider>
  )
}

export default Settings
