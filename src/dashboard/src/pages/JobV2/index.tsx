import React, {
  FunctionComponent,
  ChangeEvent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react';
import {
  Link,
  useParams
} from 'react-router-dom';
import Helmet from 'react-helmet';
import {
  Container,
  IconButton,
  Paper,
  Tabs,
  Tab,
  Toolbar,
  Typography,
  Tooltip,
  Icon
} from '@material-ui/core';
import {
  ArrowBack
} from '@material-ui/icons';
import SwipeableViews from 'react-swipeable-views';
import { useSnackbar } from 'notistack';
import useFetch from 'use-http-2';

import UserContext from '../../contexts/User';
import ClustersContext from '../../contexts/Clusters';
import Loading from '../../components/Loading';

import useActions from '../../hooks/useActions';

import Context from './Context';
import Brief from './Brief';
import Endpoints from './Endpoints';
import Metrics from './Metrics';
import Console from './Console';

interface RouteParams {
  clusterId: string;
  jobId: string;
}

const JobToolbar: FunctionComponent<{ manageable: boolean }> = ({ manageable }) => {
  const { clusterId, jobId } = useParams<RouteParams>();
  const { cluster, job } = useContext(Context);
  const { approve, kill, pause, resume } = useActions(clusterId);

  const availableActions = useMemo(() => {
    const actions = [];
    if (manageable && cluster.admin) actions.push(approve);
    if (manageable) actions.push(pause, resume, kill);
    return actions;
  }, [manageable, cluster.admin, approve, kill, pause, resume]);

  const actionButtons = availableActions.map((action, index) => {
    const { hidden, icon, tooltip, onClick } = action(job);
    if (hidden) return null;
    return (
      <Tooltip key={index} title={tooltip}>
        <IconButton onClick={(event) => onClick(event, job)}>
          <Icon>{icon}</Icon>
        </IconButton>
      </Tooltip>
    )
  })

  return (
    <Toolbar disableGutters variant="dense">
      <IconButton
        edge="start"
        color="inherit"
        component={Link}
        to="./"
      >
        <ArrowBack />
      </IconButton>
      <Typography variant="h6" style={{ flexGrow: 1 }}>
        {clusterId}/{jobId}
      </Typography>
      {actionButtons}
    </Toolbar>
  );
}

const ManagableJob: FunctionComponent = () => {
  const [index, setIndex] = useState(0);
  const onChange = useCallback((event: ChangeEvent<{}>, value: any) => {
    setIndex(value as number);
  }, [setIndex]);
  const onChangeIndex = useCallback((index: number, prevIndex: number) => {
    setIndex(index);
  }, [setIndex]);
  return (
    <>
      <Tabs
        value={index}
        onChange={onChange}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab label="Brief"/>
        <Tab label="Endpoints"/>
        <Tab label="Metrics"/>
        <Tab label="Console"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={onChangeIndex}
      >
        {index === 0 ? <Brief/> : <div/>}
        {index === 1 ? <Endpoints/> : <div/>}
        {index === 2 ? <Metrics/> : <div/>}
        {index === 3 ? <Console/> : <div/>}
      </SwipeableViews>
    </>
  );
}

const UnmanagableJob: FunctionComponent = () => {
  const [index, setIndex] = useState(0);
  const onChange = useCallback((event: ChangeEvent<{}>, value: any) => {
    setIndex(value as number);
  }, [setIndex]);
  const onChangeIndex = useCallback((index: number, prevIndex: number) => {
    setIndex(index);
  }, [setIndex]);
  return (
    <>
      <Tabs
        value={index}
        onChange={onChange}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab label="Brief"/>
        <Tab label="Metrics"/>
        <Tab label="Console"/>
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={onChangeIndex}
      >
        {index === 0 ? <Brief/> : <div/>}
        {index === 1 ? <Metrics/> : <div/>}
        {index === 2 ? <Console/> : <div/>}
      </SwipeableViews>
    </>
  );
}

const JobContent: FunctionComponent = () => {
  const { clusterId, jobId } = useParams<RouteParams>();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { email } = useContext(UserContext);
  const { clusters } = useContext(ClustersContext);
  const cluster = useMemo(() => {
    return clusters.filter((cluster) => cluster.id === clusterId)[0];
  }, [clusterId, clusters]);
  const { error: jobError, data: jobData, get: getJob } =
    useFetch(`/api/v2/clusters/${clusterId}/jobs/${jobId}`,
      [clusterId, jobId]);
  const { error: clusterError, data: clusterData } =
    useFetch(`/api/clusters/${clusterId}`, [clusterId]);
  const manageable = useMemo(() => {
    if (jobData === undefined) return false;
    if (cluster === undefined) return false;
    if (cluster.admin === true) return true;
    if (jobData['userName'] === email) return true;
    return false;
  }, [jobData, cluster, email]);
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

  if (job === undefined) {
    return <Loading/>;
  }

  return (
    <Context.Provider value={{ cluster: clusterData, job }}>
      <Helmet title={`(${job['jobStatus']}) ${job['jobName']}`}/>
      <Container maxWidth="lg">
        <JobToolbar manageable={manageable}/>
        <Paper elevation={2}>
          <>
            {manageable && <ManagableJob/>}
            {manageable || <UnmanagableJob/>}
          </>
        </Paper>
      </Container>
    </Context.Provider>
  );

}

const Job: FunctionComponent = () => {
  const { clusterId, jobId } = useParams<RouteParams>();
  const key = useMemo(() => `${clusterId}/${jobId}`, [clusterId, jobId]);
  return (
    <JobContent key={key}/>
  );
}

export default Job;
