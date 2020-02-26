import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import useActions from '../../hooks/useActions';

import ClusterContext from './ClusterContext';
import JobsTable from './JobsTable';
import {
  name,
  status,
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
  const { support, pause, resume, kill } = useActions(cluster.id);

  const [limit, setLimit] = useState(20);

  const { data, loading, error, get, abort } = useFetch(
    `/api/v2/clusters/${cluster.id}/teams/${selectedTeam}/jobs?limit=${limit}`,
    undefined,
    [cluster.id, selectedTeam, limit]
  );

  const { true: activeJobs, false: inactiveJobs } = useMemo(() => {
    if (data === undefined) return {};
    return groupByActive(data);
  }, [data]);

  const handleLastPage = useCallback((pageSize: number) => {
    abort();
    setLimit((limit) => limit + pageSize);
  }, [abort, setLimit]);

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
      <JobsTable
        title="Active Jobs"
        jobs={activeJobs}
        isLoading={data === undefined}
        defaultPageSize={5}
        columns={[
          name,
          status,
          gpu,
          preemptible,
          priority,
          submitted,
        ]}
        actions={[
          support,
          pause,
          resume,
          kill,
        ]}
      />
      <JobsTable
        title="Inactive Jobs"
        jobs={inactiveJobs}
        isLoading={data === undefined}
        defaultPageSize={10}
        columns={[
          name,
          status,
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
