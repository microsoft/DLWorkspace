import * as React from 'react';
import {
  FunctionComponent,
  useContext
} from 'react';

import {
  Card,
  CardMedia,
  CardHeader
} from '@material-ui/core';


import TeamContext from '../../contexts/Team';

interface Props {
  data: any;
}

const Metrics: FunctionComponent<Props> = ({ data: { config } }) => {
  const { currentTeamId } = useContext(TeamContext);

  return (
    <>
      <Card>
        <CardHeader title="Team GPU Usage"/>
        <CardMedia
          component="iframe"
          src={`${config['grafana']}/dashboard/db/per-vc-gpu-statistic?var-vc_name=${currentTeamId}`}
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
