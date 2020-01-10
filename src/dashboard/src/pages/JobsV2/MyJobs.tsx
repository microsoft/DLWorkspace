import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import MaterialTable, { Column, Options } from 'material-table';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import useActions from '../../hooks/useActions';
import Loading from '../../components/Loading';

import ClusterContext from './ClusterContext';
import { renderId, renderGPU, sortGPU, renderStatus, renderDate, sortDate } from './tableUtils';
import PriorityField from './PriorityField';

const getSubmittedDate = (job: any) => new Date(job['jobTime']);
const getStartedDate = (job: any) => new Date(
  job['jobStatusDetail'] && job['jobStatusDetail'][0] && job['jobStatusDetail'][0]['startedAt']);
const getFinishedDate = (job: any) => new Date(
  job['jobStatusDetail'] && job['jobStatusDetail'][0] && job['jobStatusDetail'][0]['finishedAt']);

interface JobsTableProps {
  jobs: any[];
  onExpectMoreJobs: (length: number) => void;
}

const JobsTable: FunctionComponent<JobsTableProps> = ({ jobs, onExpectMoreJobs }) => {
  const { cluster } = useContext(ClusterContext);
  const [pageSize, setPageSize] = useState(10);
  const onChangeRowsPerPage = useCallback((pageSize: number) => {
    setPageSize(pageSize);
  }, [setPageSize]);
  const onChangePage = useCallback((page: number) => {
    const maxPage = Math.ceil(jobs.length / pageSize) - 1;
    if (page >= maxPage) {
      onExpectMoreJobs(pageSize);
    }
  }, [jobs, pageSize, onExpectMoreJobs]);
  const renderPrioirty = useCallback((job: any) => (
    <PriorityField job={job}/>
  ), [])

  const columns = useMemo<Array<Column<any>>>(() => [
    { title: 'Id', type: 'string', field: 'jobId',
      render: renderId, disableClick: true },
    { title: 'Name', type: 'string', field: 'jobName' },
    { title: 'Status', type: 'string', field: 'jobStatus', render: renderStatus },
    { title: 'GPU', type: 'numeric',
      render: renderGPU, customSort: sortGPU },
    { title: 'Preemptible', type: 'boolean', field: 'jobParams.preemptionAllowed'},
    { title: 'Priority', type: 'numeric',
      render: renderPrioirty, disableClick: true },
    { title: 'Submitted', type: 'datetime',
      render: renderDate(getSubmittedDate), customSort: sortDate(getSubmittedDate) },
    { title: 'Started', type: 'datetime',
      render: renderDate(getStartedDate), customSort: sortDate(getStartedDate) },
    { title: 'Finished', type: 'datetime',
      render: renderDate(getFinishedDate), customSort: sortDate(getFinishedDate) },
  ], [renderPrioirty]);
  const options = useMemo<Options>(() => ({
    padding: 'dense',
    actionsColumnIndex: -1,
    pageSize
  }), [pageSize]);
  const { support, pause, resume, kill } = useActions(cluster.id);
  const actions = [support, pause, resume, kill];

  return (
    <MaterialTable
      title="My Jobs"
      columns={columns}
      data={jobs}
      options={options}
      actions={actions}
      onChangeRowsPerPage={onChangeRowsPerPage}
      onChangePage={onChangePage}
    />
  );
};

const MyJobs: FunctionComponent = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { cluster } = useContext(ClusterContext);
  const { selectedTeam } = useContext(TeamsContext);
  const [limit, setLimit] = useState(20);
  const { error, data, get } = useFetch(
    `/api/v2/clusters/${cluster.id}/teams/${selectedTeam}/jobs?limit=${limit}`,
    [cluster.id, selectedTeam, limit]
  );
  const [jobs, setJobs] = useState<any[]>();
  const onExpectMoreJobs = useCallback((count: number) => {
    setLimit((limit: number) => limit + count);
  }, []);
  useEffect(() => {
    setJobs(undefined);
    setLimit(20);
  }, [cluster.id]);
  useEffect(() => {
    if (data !== undefined) {
      setJobs(data);
      const timeout = setTimeout(get, 3000);
      return () => {
        clearTimeout(timeout);
      }
    }
  }, [data, get]);
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

  if (jobs !== undefined) return (
    <JobsTable
      jobs={jobs}
      onExpectMoreJobs={onExpectMoreJobs}
    />
  );
  if (error) return null;

  return <Loading/>;
};

export default MyJobs;
