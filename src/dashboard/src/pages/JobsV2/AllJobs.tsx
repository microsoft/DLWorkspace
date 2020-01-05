import React, {
  FunctionComponent,
  KeyboardEvent,
  useCallback,
  useContext,
  useState,
  useEffect,
  useMemo,
  useRef
} from 'react';
import { useHistory } from 'react-router-dom';
import { Button, TextField } from '@material-ui/core';
import MaterialTable, { Column, Options } from 'material-table';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import Loading from '../../components/Loading';
import useActions from '../../hooks/useActions';

import ClusterContext from './ClusterContext';
import { renderDate, sortDate, renderStatus } from './tableUtils';

const renderUser = (job: any) => job['userName'].split('@', 1)[0];

const getSubmittedDate = (job: any) => new Date(job['jobTime']);
const getStartedDate = (job: any) => new Date(job['jobStatusDetail'] && job['jobStatusDetail'][0]['startedAt']);
const getFinishedDate = (job: any) => new Date(job['jobStatusDetail'] && job['jobStatusDetail'][0]['finishedAt']);

interface PriorityFieldProps {
  job: any;
}

const PriorityField: FunctionComponent<PriorityFieldProps> = ({ job }) => {
  const { enqueueSnackbar } = useSnackbar();
  const { cluster } = useContext(ClusterContext);
  const [editing, setEditing] = useState(false);
  const [disabled, setDisabled] = useState(false);
  const input = useRef<HTMLInputElement>();
  const setPriority = useCallback((priority: number) => {
    if (priority === job['priority']) return;
    enqueueSnackbar('Priority is being set...');
    setDisabled(true);

    fetch(`/api/clusters/${cluster.id}/jobs/${job['jobId']}/priority`, {
      method: 'PUT',
      body: JSON.stringify({ priority }),
      headers: { 'Content-Type': 'application/json' }
    }).then((response) => {
      if (response.ok) {
        enqueueSnackbar('Priority is set successfully', { variant: 'success' });
      } else {
        throw Error();
      }
      setEditing(false);
    }).catch(() => {
      enqueueSnackbar('Failed to set priority', { variant: 'error' });
    }).then(() => {
      setDisabled(false);
    });
  }, [enqueueSnackbar, job, cluster.id]);
  const onBlur = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    setEditing(false);
    if (input.current) {
      setPriority(input.current.valueAsNumber);
    }
  }, [setPriority]);
  const onKeyDown = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && input.current) {
      setPriority(input.current.valueAsNumber);
    }
    if (event.key === 'Escape') {
      setEditing(false);
    }
  }, [setPriority, setEditing]);
  const onClick = useCallback(() => {
    setEditing(true);
  }, [setEditing])

  const component = editing ? (
    <TextField
      inputRef={input}
      type="number"
      defaultValue={job['priority']}
      disabled={disabled}
      fullWidth
      onBlur={onBlur}
      onKeyDown={onKeyDown}
    />
  ) : (
    <Button fullWidth onClick={onClick}>
      {job['priority']}
    </Button>
  );

  return component;
}

interface JobsTableProps {
  title: string;
  jobs: any[];
}

const JobsTable: FunctionComponent<JobsTableProps> = ({ title, jobs }) => {
  const history = useHistory();
  const { cluster } = useContext(ClusterContext);

  const onRowClick = useCallback((event: any, job: any) => {
    const e = encodeURIComponent;
    const to = `/jobs-v2/${e(cluster.id)}/${e(job['jobId'])}`
    history.push(to);
  }, [cluster.id, history]);
  const [pageSize, setPageSize] = useState(5);
  const onChangeRowsPerPage = useCallback((pageSize: number) => {
    setPageSize(pageSize);
  }, [setPageSize]);

  const renderPrioirty = useCallback((job: any) => (
    <PriorityField job={job}/>
  ), [])

  const columns = useMemo<Array<Column<any>>>(() => [
    { title: 'Id', type: 'string', field: 'jobId' },
    { title: 'Name', type: 'string', field: 'jobName' },
    { title: 'Status', type: 'string', field: 'jobStatus', render: renderStatus },
    { title: 'GPU', type: 'numeric', field: 'jobParams.resourcegpu' },
    { title: 'User', type: 'string', render: renderUser},
    { title: 'Preempable', type: 'boolean', field: 'jobParams.preemptionAllowed'},
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
  const { approve, kill, pause, resume } = useActions(cluster.id);
  const actions = [approve, pause, resume, kill];

  return (
    <MaterialTable
      title={title}
      columns={columns}
      data={jobs}
      options={options}
      actions={actions}
      onRowClick={onRowClick}
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
