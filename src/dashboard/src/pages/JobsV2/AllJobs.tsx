import React, {
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
  user,
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

const MyJobs: FunctionComponent = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { cluster } = useContext(ClusterContext);
  const { selectedTeam } = useContext(TeamsContext);
  const {
    support, approve, pause, resume, kill,
    batchApprove, batchPause, batchResume, batchKill
  } = useActions(cluster.id);

  const [limit, setLimit] = useState(30);

  const { data, loading, error, get, abort } = useFetch(
    `/api/v2/clusters/${cluster.id}/teams/${selectedTeam}/jobs?user=all&limit=${limit}`,
    undefined,
    [cluster.id, selectedTeam, limit]
  );

  const { true: activeJobs, false: inactiveJobs } = useMemo(() => {
    if (data === undefined) return {};
    return groupByActive(data);
  }, [data]);

  const handleLastPage = useCallback((pageSize: number) => {
    abort();
    setLimit((limit) => Math.ceil((limit + pageSize) / pageSize) * pageSize);
  }, [abort, setLimit]);

  const title = useMemo(() => {
    if (data === undefined) return cluster.id;
    if (activeJobs === undefined) {
      return `(0) ${cluster.id}`;
    }
    return `(${activeJobs.length}) ${cluster.id}`;
  }, [data, activeJobs, cluster]);

  const actions = useMemo(() => {
    if (cluster.admin) {
      return [
        support,
        approve,
        pause,
        resume,
        kill,
        batchApprove,
        batchPause,
        batchResume,
        batchKill
      ];
    } else {
      return [support];
    }
  }, [
    cluster.admin,
    support,
    approve,
    pause,
    resume,
    kill,
    batchApprove,
    batchPause,
    batchResume,
    batchKill
  ]);

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
      <JobsTable
        title="Active Jobs"
        jobs={activeJobs}
        isLoading={data === undefined}
        defaultPageSize={5}
        selection
        columns={[
          name,
          user,
          status,
          type,
          gpu,
          preemptible,
          priority,
          submitted,
        ]}
        actions={actions}
      />
      <JobsTable
        title="Inactive Jobs"
        jobs={inactiveJobs}
        isLoading={data === undefined}
        defaultPageSize={10}
        columns={[
          name,
          user,
          status,
          type,
          gpu,
          preemptible,
          priority,
          finished,
        ]}
        actions={[
          support,
        ]}
        onLastPage={handleLastPage}
      />
    </>
  );
};

export default MyJobs;
