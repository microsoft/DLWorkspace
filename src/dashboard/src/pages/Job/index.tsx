import React, {
  FunctionComponent,
  useContext,
  useEffect,
  useMemo
} from 'react';
import { capitalize } from 'lodash';
import { usePrevious } from 'react-use';
import Helmet from 'react-helmet';
import {
  Container,
} from '@material-ui/core';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import UserContext from '../../contexts/User';
import TeamsContext from '../../contexts/Teams';
import Loading from '../../components/Loading';

import useRouteParams from './useRouteParams';
import Context from './Context';
import Header from './Header';
import Tabs from './Tabs';

const JobContent: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();

  const { email } = useContext(UserContext);
  const { teams } = useContext(TeamsContext);

  const { data: job, loading: jobLoading, error: jobError, get: getJob } =
    useFetch(`/api/v2/clusters/${clusterId}/jobs/${jobId}`, undefined, [clusterId, jobId]);

  const { data: cluster, error: clusterError } =
    useFetch(`/api/clusters/${clusterId}`, undefined, [clusterId]);

  const teamCluster = useMemo(() => {
    if (job === undefined) return undefined;
    const team = teams.filter((team: any) => team.id === job['vcName'])[0];
    if (team === undefined) return undefined;
    const teamCluster = team.clusters.filter((cluster: any) => cluster.id === clusterId)[0];
    return teamCluster;
  }, [job, teams, clusterId]);
  const accessible = useMemo(() => {
    return teamCluster !== undefined;
  }, [teamCluster]);
  const admin = useMemo(() => {
    return accessible && Boolean(teamCluster.admin);
  }, [accessible, teamCluster]);

  const manageable = useMemo(() => {
    if (job === undefined) return false;
    if (admin === true) return true;
    if (job['userName'] === email) return true;
    return false;
  }, [job, admin, email]);

  useEffect(() => {
    if (jobError !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch job: ${clusterId}/${jobId}`, {
        variant: 'error',
        persist: true
      });
      return () => {
        if (key !== null) closeSnackbar(key);
      }
    }
  }, [jobError, enqueueSnackbar, closeSnackbar, clusterId, jobId]);

  useEffect(() => {
    if (clusterError !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch cluster config: ${clusterId}`, {
        variant: 'error',
        persist: true
      });
      return () => {
        if (key !== null) closeSnackbar(key);
      }
    }
  }, [clusterError, enqueueSnackbar, closeSnackbar, clusterId]);

  useEffect(() => { // refresh job info
    if (jobLoading) return;

    const timeout = setTimeout(getJob, 3000);
    return () => {
      clearTimeout(timeout);
    };
  }, [jobLoading, getJob]);

  const status = useMemo(() => job && job['jobStatus'], [job]);
  const previousStatus = usePrevious(status);
  useEffect(() => {
    if (previousStatus !== undefined && status !== previousStatus) {
      enqueueSnackbar(`Job is ${status} now.`, { variant: "info" });
    }
  }, [previousStatus, status, enqueueSnackbar])

  if (cluster === undefined || job === undefined) {
    return <Loading/>;
  }

  return (
    <Context.Provider value={{ cluster, accessible, admin, job }}>
      <Helmet title={`(${capitalize(job['jobStatus'])}) ${job['jobName']}`}/>
      <Container fixed maxWidth="lg">
        <Header manageable={manageable}/>
        <Tabs manageable={manageable}/>
      </Container>
    </Context.Provider>
  );
}

const Job: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const key = useMemo(() => `${clusterId}/${jobId}`, [clusterId, jobId]);
  return (
    <JobContent key={key}/>
  );
}

export default Job;
