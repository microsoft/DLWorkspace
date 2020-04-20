import React, { FunctionComponent } from 'react';

import { Card, Divider } from '@material-ui/core';

import { ClusterProvider } from './Context';
import ClusterCardHeader from './ClusterCardHeader';
import ResourceChart from './ResourceChart';
import StorageList from './StorageList';
import ClusterCardActions from './ClusterCardActions';

interface Props {
  clusterId: string;
}

const ClusterCard: FunctionComponent<Props> = ({ clusterId }) => (
  <ClusterProvider id={clusterId}>
    <Card>
      <ClusterCardHeader/>
      <Divider/>
      <ResourceChart/>
      <Divider/>
      <StorageList/>
      <Divider/>
      <ClusterCardActions/>
    </Card>
  </ClusterProvider>
);

export default ClusterCard;
