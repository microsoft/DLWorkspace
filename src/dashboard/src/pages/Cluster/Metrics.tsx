import React, {
  FunctionComponent,
  useContext} from 'react';

import {
  Card,
  CardMedia,
  CardHeader
} from '@material-ui/core';


import TeamsContext from '../../contexts/Teams';

interface Props {
  data: any;
}

const Metrics: FunctionComponent<Props> = ({ data: { config } }) => {
  const { selectedTeam } = useContext(TeamsContext);

  return (
    <>
      <Card>
        <CardHeader title="Team GPU Usage"/>
        <CardMedia
          component="iframe"
          src={`${config['grafana']}/dashboard/db/per-vc-gpu-statistic?var-vc_name=${selectedTeam}`}
          height="480"
          frameBorder="0"
        />
      </Card>
      <Card>
        <CardHeader title="Cluster GPU Usage"/>
        <CardMedia
          component="iframe"
          src={`${config['grafana']}/dashboard/db/gpu-usage?refresh=30s&orgId=1`}
          height="480"
          frameBorder="0"
        />
      </Card>
    </>
  );
};

export default Metrics;
