import React, {
  FunctionComponent,
  useMemo
} from 'react';

import {
  Card,
  CardMedia
} from '@material-ui/core';

import useFetch from 'use-http-2';

import Loading from '../../components/Loading';

import useRouteParams from './useRouteParams';

const Metrics: FunctionComponent<{ data: any }> = ({ data }) => {
  const { clusterId } = useRouteParams();

  const { data: clusterConfig } = useFetch(`/api/clusters/${clusterId}`, undefined, [clusterId]);

  const url = useMemo(() => {
    if (clusterConfig === undefined) return;
    return `${clusterConfig['grafana']}/dashboard/db/node-status?orgId=1&var-node=${data.ip}`;
  }, [clusterConfig, data]);

  if (clusterConfig === undefined) {
    return <Loading/>;
  }

  return (
    <Card>
      <CardMedia
        component="iframe"
        src={url}
        height="1200"
        frameBorder="0"
      />
    </Card>
  );
};

export default Metrics;
