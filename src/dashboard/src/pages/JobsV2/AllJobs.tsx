import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useState,
  useEffect,
  useMemo
} from 'react';
import MaterialTable, { Column, Options } from 'material-table';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import Loading from '../../components/Loading';
import useActions from '../../hooks/useActions';

import ClusterContext from './ClusterContext';
import { renderId, renderGPU, sortGPU, renderDate, sortDate, renderStatus } from './tableUtils';
import PriorityField from './PriorityField';

const renderUser = (job: any) => job['userName'].split('@', 1)[0];

const getSubmittedDate = (job: any) => new Date(job['jobTime']);
const getStartedDate = (job: any) => new Date(job['jobStatusDetail'] && job['jobStatusDetail'][0]['startedAt']);
const getFinishedDate = (job: any) => new Date(job['jobStatusDetail'] && job['jobStatusDetail'][0]['finishedAt']);

interface JobsTableProps {
  title: string;
  jobs: any[];
}

const JobsTable: FunctionComponent<JobsTableProps> = ({ title, jobs }) => {
  const { cluster } = useContext(ClusterContext);
  const [pageSize, setPageSize] = useState(5);
  const onChangeRowsPerPage = useCallback((pageSize: number) => {
    setPageSize(pageSize);
  }, [setPageSize]);

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
    { title: 'User', type: 'string', render: renderUser},
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
    actionsColumnIndex: -1,
    pageSize,
    padding: 'dense'
  }), [pageSize]);
  const { support, approve, kill, pause, resume } = useActions(cluster.id);
  const actions = [support, approve, pause, resume, kill];

  return (
    <MaterialTable
      title={title}
      columns={columns}
      data={jobs}
      options={options}
      actions={actions}
      onChangeRowsPerPage={onChangeRowsPerPage}
    />
  );
}

const AllJobs: FunctionComponent = () => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { cluster } = useContext(ClusterContext);
  const { selectedTeam } = useContext(TeamsContext);
  const { error, data, get } = useFetch(
    `/api/v2/clusters/${cluster.id}/teams/${selectedTeam}/jobs?user=all&limit=100`,
    [cluster.id, selectedTeam]
  );
  const [jobs, setJobs] = useState<any[]>();
  useEffect(() => {
    setJobs(undefined);
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

  const runningJobs = useMemo(() => {
    if (jobs === undefined) return undefined;
    const runningJobs = jobs.filter((job: any) => job['jobStatus'] === 'running');
    if (runningJobs.length === 0) return undefined;
    return runningJobs;
  }, [jobs]);
  const queuingJobs = useMemo(() => {
    if (jobs === undefined) return undefined;
    const queuingJobs = jobs.filter((job: any) => job['jobStatus'] === 'queued' || job['jobStatus'] === 'scheduling' );
    if (queuingJobs.length === 0) return undefined;
    return queuingJobs
  }, [jobs]);
  const unapprovedJobs = useMemo(() => {
    if (jobs === undefined) return undefined;
    const unapprovedJobs = jobs.filter((job: any)=>job['jobStatus'] === 'unapproved');
    if (unapprovedJobs.length === 0) return undefined;
    return unapprovedJobs
  }, [jobs]);
  const pausedJobs = useMemo(() => {
    if (jobs === undefined) return undefined;
    const pausedJobs = jobs.filter((job: any) => job['jobStatus'] === 'paused' || job['jobStatus'] === 'pausing' );
    if (pausedJobs.length === 0) return undefined;
    return pausedJobs
  }, [jobs]);

  if (jobs !== undefined) return (
    <>
      {runningJobs && <JobsTable title="Running Jobs" jobs={runningJobs}/>}
      {queuingJobs && <JobsTable title="Queuing Jobs" jobs={queuingJobs}/>}
      {unapprovedJobs && <JobsTable title="Unapproved Jobs" jobs={unapprovedJobs}/>}
      {pausedJobs && <JobsTable title="Pauses Jobs" jobs={pausedJobs}/>}
      {jobs.length === 0 && <JobsTable title="All Jobs" jobs={jobs} />}
    </>
  );
  if (error !== undefined) return null;

  return <Loading/>;
};

export default AllJobs;
