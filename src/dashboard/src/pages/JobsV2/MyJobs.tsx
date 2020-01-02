import React, {
  FunctionComponent,
  MouseEvent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import { useHistory } from 'react-router-dom';
import MaterialTable, { Column, Options } from 'material-table';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';

import Loading from '../../components/Loading';
import Error from '../../components/Error';

import ClusterContext from './ClusterContext';
import useActions from './useActions';
import { renderDate, sortDate } from './tableUtils';

const getSubmittedDate = (job: any) => new Date(job['jobTime']);
const getStartedDate = (job: any) => new Date(job['jobStatusDetail'] && job['jobStatusDetail'][0]['startedAt']);
const getFinishedDate = (job: any) => new Date(job['jobStatusDetail'] && job['jobStatusDetail'][0]['finishedAt']);

interface JobsTableProps {
  jobs: any[];
  onExpectMoreJobs: (length: number) => void;
}

const JobsTable: FunctionComponent<JobsTableProps> = ({ jobs, onExpectMoreJobs }) => {
  const history = useHistory();
  const { cluster } = useContext(ClusterContext);

  const onRowClick = useCallback((event: any, job: any) => {
    const e = encodeURIComponent;
    const to = `/job/${e(job['vcName'])}/${e(cluster.id)}/${e(job['jobId'])}`
    history.push(to);
  }, [cluster.id, history]);
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

  const columns = useMemo<Array<Column<any>>>(() => [
    { title: 'Id', type: 'string', field: 'jobId' },
    { title: 'Name', type: 'string', field: 'jobName' },
    { title: 'Status', type: 'string', field: 'jobStatus' },
    { title: 'GPU', type: 'numeric', field: 'jobParams.resourcegpu' },
    { title: 'Preempable', type: 'boolean', field: 'jobParams.preemptionAllowed'},
    { title: 'Submitted', type: 'datetime',
      render: renderDate(getSubmittedDate), customSort: sortDate(getSubmittedDate) },
    { title: 'Started', type: 'datetime',
      render: renderDate(getStartedDate), customSort: sortDate(getStartedDate) },
    { title: 'Finished', type: 'datetime',
      render: renderDate(getFinishedDate), customSort: sortDate(getFinishedDate) },
  ], []);
  const options = useMemo<Options>(() => ({
    actionsColumnIndex: -1,
    pageSize
  }), [pageSize]);
  const { kill, pause, resume, component } = useActions();
  const actions = [kill, pause, resume];

  return (
    <>
      <MaterialTable
        title="My Jobs"
        columns={columns}
        data={jobs}
        options={options}
        actions={actions}
        onRowClick={onRowClick}
        onChangeRowsPerPage={onChangeRowsPerPage}
        onChangePage={onChangePage}
      />
      {component}
    </>
  );
};

const MyJobs: FunctionComponent = () => {
  const { cluster } = useContext(ClusterContext);
  const { selectedTeam } = useContext(TeamsContext);
  const [limit, setLimit] = useState(20);
  const { loading, error, data, get } = useFetch(
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
    let timeout: number | undefined;
    if (data !== undefined) {
      setJobs(data);
      timeout = setTimeout(get, 10000);
    }
    return () => {
      if (timeout !== undefined) {
        clearTimeout(timeout);
      }
    }
  }, [data, get]);

  if (jobs !== undefined) return (
    <JobsTable
      jobs={jobs}
      onExpectMoreJobs={onExpectMoreJobs}
    />
  );
  if (loading) return <Loading/>;
  if (error) return <Error message="Failed to fetch the data, try reloading the page."/>;

  return null;
};

export default MyJobs;
