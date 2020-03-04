import React, {
  FunctionComponent,
  useContext,
  useMemo
} from 'react';
import { useParams } from 'react-router';

import {
  Card,
  CardMedia,
  CardHeader
} from '@material-ui/core';

import useFetch from 'use-http-2';

import TeamsContext from '../../contexts/Teams';
import Loading from '../../components/Loading';

const Metrics: FunctionComponent = () => {
  const { clusterId } = useParams();
  const { selectedTeam } = useContext(TeamsContext);

  const { data } = useFetch(`/api/clusters/${clusterId}`, undefined, [clusterId]);

  const vcUrl = useMemo(() => {
    if (data === undefined) return;
    return `${data['grafana']}/dashboard/db/per-vc-gpu-statistic?var-vc_name=${selectedTeam}`;
  }, [data, selectedTeam]);
  const clusterUrl = useMemo(() => {
    if (data === undefined) return;
    return `${data['grafana']}/dashboard/db/gpu-usage?refresh=30s&orgId=1`;
  }, [data]);

  if (data === undefined) {
    return <Loading/>;
  }

  return (
    <>
      <Card>
        <CardHeader title="Team GPU Usage"/>
        <CardMedia
          component="iframe"
          src={vcUrl}
          height="480"
          frameBorder="0"
        />
      </Card>
      <Card>
        <CardHeader title="Cluster GPU Usage"/>
        <CardMedia
          component="iframe"
          src={clusterUrl}
          height="480"
          frameBorder="0"
        />
      </Card>
    </>
  );
};

export default Metrics;
