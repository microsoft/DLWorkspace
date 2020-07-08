import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useMemo
} from 'react'

import { entries, find, get, set, zipWith } from 'lodash'

import { Link as RouterLink } from 'react-router-dom'
import {
  Container,
  Link as UILink,
  Tooltip,
  Typography
} from '@material-ui/core'

import {
  Column,
  Options
} from 'material-table'

import { useSnackbar } from 'notistack'
import useFetch from 'use-http-1'

import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable'
import TeamContext from '../../contexts/Team'
import ClustersContext from '../../contexts/Clusters'
import useTableData from '../../hooks/useTableData'

import useResourceColumns, { ResourceKind } from './useResourceColumns'
import usePrometheus from '../../hooks/usePrometheus'

const useClusterStatus = (clusterId: string) => {
  const { currentTeamId } = useContext(TeamContext)
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()

  const { data, loading, error, get } = useFetch(
    `/api/v2/clusters/${clusterId}/teams/${currentTeamId}`,
    [clusterId, currentTeamId])

  useEffect(() => {
    if (loading) return

    const timeout = setTimeout(get, 3000)
    return () => {
      clearTimeout(timeout)
    }
  }, [loading, get])
  useEffect(() => {
    if (error) {
      const key = enqueueSnackbar(`Failed to fetch status of cluster ${clusterId}`, {
        variant: 'error',
        persist: true
      })
      return () => {
        if (key != null) closeSnackbar(key)
      }
    }
  }, [error, clusterId, enqueueSnackbar, closeSnackbar])

  return data
}

const useClusterMetrics = (status: any) => { // Actually Cluster-Team Metrics
  const { currentTeamId } = useContext(TeamContext)

  const metrics = usePrometheus(status && status.config ? status.config['grafana'] : undefined,
    `avg(task_gpu_percent {vc_name="${currentTeamId}"})`)

  return get(metrics, 'result[0].value[1]')
}

const Clusters: FunctionComponent = () => {
  const { clusters } = useContext(ClustersContext)

  const clustersId = clusters.map(({ id }) => id)
  const clustersStatus = clustersId.map(useClusterStatus)
  const clustersMetrics = clustersStatus.map(useClusterMetrics)

  const clustersData = useMemo(() => zipWith(
    clustersId, clustersStatus, clustersMetrics,
    (id, status, metrics) => ({ id, status, metrics })),
  [...clustersId, ...clustersStatus, ...clustersMetrics]) // eslint-disable-line react-hooks/exhaustive-deps

  const clusterTypesStatus = useMemo(() => {
    const clusterTypesStatus = []
    for (const { id: clusterId, status: clusterStatus, metrics: clusterMetrics } of clustersData) {
      if (clusterStatus == null) {
        clusterTypesStatus.push({ id: clusterId, metrics: clusterMetrics })
        continue
      }

      const clusterSumStatus = Object.create(null)
      clusterTypesStatus.push({
        id: clusterId,
        status: clusterSumStatus,
        runningJobs: clusterStatus.runningJobs,
        metrics: clusterMetrics
      })

      for (const [typeId, typeStatus] of entries(clusterStatus.types)) {
        clusterTypesStatus.push({
          id: typeId,
          clusterId,
          status: typeStatus
        })

        for (const type of ['cpu', 'gpu', 'memory']) {
          for (const kind of ['total', 'unschedulable', 'used', 'preemptable', 'available']) {
            const path = [type, kind]
            set(clusterSumStatus, path, get(clusterSumStatus, path, 0) + get(typeStatus, path, 0))
          }
        }
      }
    }
    return clusterTypesStatus
  }, clustersData) // eslint-disable-line react-hooks/exhaustive-deps

  const data = useTableData(clusterTypesStatus)

  const resourceKinds = useRef<ResourceKind[]>(
    ['total', 'unschedulable', 'used', 'preemptable', 'available']
  ).current
  const resourceColumns = useResourceColumns(resourceKinds)
  const columns = useMemo(() => {
    const columns: Array<Column<any>> = []

    columns.push({
      field: 'id',
      render: (data) => data.clusterId == null
        ? <UILink variant="subtitle2" component={RouterLink} to={data.id}>{data.id}</UILink>
        : <Typography variant="subtitle2">{data.id}</Typography>,
      width: 'auto'
    })

    columns.push(...resourceColumns)

    columns.push({
      title: 'Assigned GPU Utilization',
      type: 'numeric',
      field: 'metrics',
      render: ({ metrics }) => metrics !== undefined ? (
        <>{Number(metrics).toFixed(2)}%</>
      ): null,
      width: 'auto'
    }, {
      title: 'Running Jobs',
      type: 'numeric',
      field: 'runningJobs',
      render: (data: any) => data.clusterId == null ? (
        <Tooltip title={`View jobs in ${data.id}`}>
          <UILink variant="subtitle2" component={RouterLink} to={`/jobs/${data.id}`}>
            {get(data, 'runningJobs', 0)}
          </UILink>
        </Tooltip>
      ) : null,
      width: 'auto'
    })

    return columns
  }, [resourceColumns])
  const options = useRef<Options>({
    padding: 'dense',
    draggable: false,
    paging: false
  }).current
  const parentChildData = useCallback(({ clusterId }, rows: any[]) => {
    return find(rows, ({ id }) => clusterId === id)
  }, [])

  return (
    <Container fixed maxWidth="xl">
      <SvgIconsMaterialTable
        title="Clusters"
        data={data}
        columns={columns}
        options={options}
        parentChildData={parentChildData}
      />
    </Container>
  )
}

export default Clusters
