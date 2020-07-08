import * as React from 'react'
import {
  ComponentPropsWithoutRef,
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'
import Helmet from 'react-helmet'
import { useSnackbar } from 'notistack'
import useFetch from 'use-http-1'
import { compact, reduce } from 'lodash'

import TeamContext from '../../contexts/Team'
import useActions from '../../hooks/useActions'
import useBatchActions from '../../hooks/useBatchActions'

import ClusterContext from './ClusterContext'
import JobsTable from './JobsTable'
import {
  status,
  type,
  gpu,
  preemptible,
  priority,
  timeout,
  submitted,
  finished,

  useNameId,
} from './JobsTable/columns'
import { groupByActiveStatus } from './utils'

type JobsTablePropsWithoutColumnsActions = Omit<ComponentPropsWithoutRef<typeof JobsTable>, 'columns' | 'actions'>

const ActiveJobsTable: FunctionComponent<JobsTablePropsWithoutColumnsActions> = (props) => {
  const { cluster } = useContext(ClusterContext)
  const { support, pause, resume, kill } = useActions(cluster.id)
  const { batchPause, batchResume, batchKill } = useBatchActions(cluster.id)

  const nameId = useNameId()
  const columns = useMemo(() => compact([
    nameId,
    status(),
    type(),
    gpu(),
    preemptible(),
    priority(),
    cluster.admin ? timeout() : undefined,
    submitted(),
  ]), [nameId, cluster.admin])
  const actions = useMemo(() => [
    support, pause, resume, kill,
    batchPause, batchResume, batchKill
  ], [
    support, pause, resume, kill,
    batchPause, batchResume, batchKill
  ])
  return (
    <JobsTable
      columns={columns}
      actions={actions}
      {...props}
    />
  )
}

const InactiveJobsTable: FunctionComponent<JobsTablePropsWithoutColumnsActions> = (props) => {
  const { cluster } = useContext(ClusterContext)
  const { support } = useActions(cluster.id)
  const nameId = useNameId()
  const columns = useMemo(() => [
    nameId,
    status(),
    type(),
    gpu(),
    preemptible(),
    priority(),
    finished(),
  ], [nameId])
  const actions = useMemo(() => [support], [support])
  return (
    <JobsTable
      columns={columns}
      actions={actions}
      {...props}
    />
  )
}

const MyJobs: FunctionComponent = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { cluster } = useContext(ClusterContext)
  const { currentTeamId } = useContext(TeamContext)

  const [limit, setLimit] = useState(30)

  const { data, loading, error, get, abort } = useFetch(
    `/api/v2/clusters/${cluster.id}/teams/${currentTeamId}/jobs?limit=${limit}`,
    [cluster.id, currentTeamId, limit]
  )

  const { Inactive: inactiveJobs = [], ...activeStatusesJobs } = useMemo(() => {
    if (data === undefined) return {}
    return groupByActiveStatus(data)
  }, [data])

  const handleLastPage = useCallback((pageSize: number) => {
    abort()
    setLimit((limit) => Math.ceil((limit + pageSize) / pageSize) * pageSize)
  }, [abort, setLimit])

  const title = useMemo(() => {
    if (data === undefined) return cluster.id
    const length = reduce(activeStatusesJobs, (length, jobs) => length + jobs.length, 0)
    return `(${length}) ${cluster.id}`
  }, [data, activeStatusesJobs, cluster])

  useEffect(() => {
    if (loading === false) {
      const timeout = setTimeout(get, 3000)
      return () => {
        clearTimeout(timeout)
      }
    }
  }, [loading, get])

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch jobs from cluster: ${cluster.id}`, {
        variant: 'error',
        persist: true
      })
      return () => {
        if (key !== null) closeSnackbar(key)
      }
    }
  }, [error, enqueueSnackbar, closeSnackbar, cluster.id])

  return (
    <>
      { title && <Helmet title={title}/> }
      { ['Running', 'Pending', 'Unapproved', 'Paused'].map(
        status => activeStatusesJobs[status] && (
          <ActiveJobsTable
            key={status}
            title={`${status} Jobs`}
            jobs={activeStatusesJobs[status]}
            defaultPageSize={5}
            selection
          />
        )
      ) }
      <InactiveJobsTable
        title="Inactive Jobs"
        jobs={inactiveJobs}
        isLoading={data === undefined}
        defaultPageSize={10}
        onLastPage={handleLastPage}
      />
    </>
  )
}

export default MyJobs
