import React, {
  FunctionComponent,
  useContext,
  useEffect,
  useMemo,
  useState
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
import ClustersContext from '../../contexts/Clusters';
import Loading from '../../components/Loading';

import useRouteParams from './useRouteParams';
import Context from './Context';
import Header from './Header';
import Tabs from './Tabs';

const JobContent: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();

  const { email } = useContext(UserContext);
  const { clusters } = useContext(ClustersContext);

  const teamCluster = useMemo(() => {
    return clusters.filter((cluster) => cluster.id === clusterId)[0];
  }, [clusters, clusterId]);
  const accessible = useMemo(() => {
    return teamCluster !== undefined;
  }, [teamCluster]);
  const admin = useMemo(() => {
    return accessible && Boolean(teamCluster.admin);
  }, [accessible, teamCluster]);

  const { error: jobError, data: jobData, get: getJob } =
    useFetch(`/api/v2/clusters/${clusterId}/jobs/${jobId}`,
      [clusterId, jobId]);
  const { error: clusterError, data: cluster } =
    useFetch(`/api/clusters/${clusterId}`, [clusterId]);

  const manageable = useMemo(() => {
    if (jobData === undefined) return false;
    if (admin === true) return true;
    if (jobData['userName'] === email) return true;
    return false;
  }, [jobData, admin, email]);

  const [job, setJob] = useState<any>();

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
  }, [clusterError, enqueueSnackbar, closeSnackbar, clusterId, jobId]);

  useEffect(() => {
    if (jobData !== undefined) {
      setJob(jobData);

      const timeout = setTimeout(getJob, 3000);
      return () => {
        clearTimeout(timeout);
      }
    }
  }, [jobData, getJob]);

  const status = useMemo(() => job && job['jobStatus'], [job]);
  const previousStatus = usePrevious(status);
  if (previousStatus !== undefined && status !== previousStatus) {
    enqueueSnackbar(`Job is ${status} now.`, { variant: "info" });
  }

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
