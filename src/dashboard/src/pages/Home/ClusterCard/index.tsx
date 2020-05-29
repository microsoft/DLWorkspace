import * as React from 'react';
import { FunctionComponent } from 'react';

import { Card, Divider } from '@material-ui/core';

import { ClusterProvider } from './Context';
import ClusterCardHeader from './ClusterCardHeader';
import ResourceChart from './ResourceChart';
import StorageList from './StorageList';
import ClusterCardActions from './ClusterCardActions';
import DirectoryContent from './DirectoryContent';

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
      <Divider/>
      <DirectoryContent/>
    </Card>
  </ClusterProvider>
);

export default ClusterCard;
