import React, {
  ComponentPropsWithoutRef,
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import Helmet from 'react-helmet';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import useActions from '../../hooks/useActions';

import ClusterContext from './ClusterContext';
import JobsTable from './JobsTable';
import {
  name,
  status,
  type,
  gpu,
  preemptible,
  priority,
  submitted,
  finished,
} from './JobsTable/columns';
import { groupByActive } from './utils';

type JobsTablePropsWithoutColumnsActions = Omit<ComponentPropsWithoutRef<typeof JobsTable>, 'columns' | 'actions'>

const ActiveJobsTable: FunctionComponent<JobsTablePropsWithoutColumnsActions> = (props) => {
  const { cluster } = useContext(ClusterContext);
  const {
    support, pause, resume, kill,
    batchPause, batchResume, batchKill
  } = useActions(cluster.id);
  const columns = useMemo(() => [
    name(),
    status(),
    type(),
    gpu(),
    preemptible(),
    priority(),
    submitted(),
  ], []);
  const actions = useMemo(() => [
    support, pause, resume, kill,
    batchPause, batchResume, batchKill
  ], [
    support, pause, resume, kill,
    batchPause, batchResume, batchKill
  ]);
  return (
    <JobsTable
      columns={columns}
      actions={actions}
      {...props}
    />
  );
};

const InactiveJobsTable: FunctionComponent<JobsTablePropsWithoutColumnsActions> = (props) => {
  const { cluster } = useContext(ClusterContext);
  const { support } = useActions(cluster.id);
  const columns = useMemo(() => [
    name(),
    status(),
    type(),
    gpu(),
    preemptible(),
    priority(),
    finished(),
  ], []);
  const actions = useMemo(() => [support], [support]);
  return (
    <JobsTable
      columns={columns}
      actions={actions}
      {...props}
    />
  );
};

const MyJobs: FunctionComponent = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { cluster } = useContext(ClusterContext);
  const { selectedTeam } = useContext(TeamsContext);

  const [limit, setLimit] = useState(30);

  const { data, loading, error, get, abort } = useFetch(
    `/api/v2/clusters/${cluster.id}/teams/${selectedTeam}/jobs?limit=${limit}`,
    undefined,
    [cluster.id, selectedTeam, limit]
  );

  const { true: activeJobs=[], false: inactiveJobs=[] } = useMemo(() => {
    if (data === undefined) return {};
    return groupByActive(data);
  }, [data]);

  const handleLastPage = useCallback((pageSize: number) => {
    abort();
    setLimit((limit) => Math.ceil((limit + pageSize) / pageSize) * pageSize);
  }, [abort, setLimit]);

  const title = useMemo(() => {
    if (data === undefined) return cluster.id;
    return `(${activeJobs.length}) ${cluster.id}`;
  }, [data, activeJobs, cluster]);

  useEffect(() => {
    if (loading === false) {
      const timeout = setTimeout(get, 3000);
      return () => {
        clearTimeout(timeout);
      }
    }
  }, [loading, get]);

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch jobs from cluster: ${cluster.id}`, {
        variant: 'error',
        persist: true
      });
      return () => {
        if (key !== null) closeSnackbar(key);
      }
    }
  }, [error, enqueueSnackbar, closeSnackbar, cluster.id]);

  return (
    <>
      { title && <Helmet title={title}/> }
      <ActiveJobsTable
        title="Active Jobs"
        jobs={activeJobs}
        isLoading={data === undefined}
        defaultPageSize={5}
        selection
      />
      <InactiveJobsTable
        title="Inactive Jobs"
        jobs={inactiveJobs}
        isLoading={data === undefined}
        defaultPageSize={10}
        onLastPage={handleLastPage}
      />
    </>
  );
};

export default MyJobs;
