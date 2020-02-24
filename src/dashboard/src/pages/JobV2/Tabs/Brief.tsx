import React, {
  FunctionComponent,
  useContext
} from 'react';
import {
  Box,
  Divider,
  List,
  ListItem,
  ListItemText
} from '@material-ui/core';

import {
  AccountBox,
  Check,
  Close,
  Group
} from '@material-ui/icons';

import CodeBlock from '../../../components/CodeBlock';
import CopyableTextListItem from '../../../components/CopyableTextListItem';

import useRouteParams from '../useRouteParams';
import Context from '../Context';

const Brief: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { cluster, job } = useContext(Context);

  return (
    <List dense>
      <CopyableTextListItem
        primary="Job Link"
        secondary={`${window.location.origin}/jobs-v2/${encodeURIComponent(clusterId)}/${encodeURIComponent(jobId)}`}
      />
      <ListItem>
        <ListItemText
          primary="Job Owner"
          secondary={(
            <Box display="flex" alignItems="center">
              <Group/>
              <Box paddingLeft={1} paddingRight={2}>{job['vcName']}</Box>
              <AccountBox/>
              <Box paddingLeft={1}>{job['userName']}</Box>
            </Box>
          )}
          secondaryTypographyProps={{ component: 'div' }}
        />
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Job Submission Time"
          secondary={new Date(job['jobTime']).toLocaleString()}
        />
      </ListItem>
      <Divider />
      <ListItem>
        <ListItemText primary="Docker Image" secondary={job['jobParams']['image']}/>
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Command"
          secondary={<CodeBlock>{job['jobParams']['cmd']}</CodeBlock>}
          secondaryTypographyProps={{ component: 'div' }}
        />
      </ListItem>
      <Divider />
      <CopyableTextListItem
        primary="Data Path"
        secondary={`${cluster['dataStorage'] || ''}/${job['jobParams']['dataPath']}`}
      />
      <CopyableTextListItem
        primary="Work Path"
        secondary={`${cluster['workStorage'] || ''}/${job['jobParams']['workPath']}`}
      />
      <CopyableTextListItem
        primary="Job Path"
        secondary={`${cluster['workStorage'] || ''}/${job['jobParams']['jobPath']}`}
      />
      <Divider />
      <ListItem>
        <ListItemText
          primary="Cluster"
          secondary={clusterId}
        />
      </ListItem>
      {
        job['jobParams']['jobtrainingtype'] === 'PSDistJob' && (
          <ListItem>
            <ListItemText
              primary="Number of Nodes"
              secondary={job['jobParams']['numpsworker']}
            />
          </ListItem>
        )
      }
      {
        job['jobParams']['jobtrainingtype'] === 'PSDistJob' && (
          <ListItem>
            <ListItemText
              primary="Total of GPUs"
              secondary={job['jobParams']['numpsworker'] * job['jobParams']['resourcegpu']}
            />
          </ListItem>
        )
      }
      {
        job['jobParams']['jobtrainingtype'] === 'RegularJob' && (
          <ListItem>
            <ListItemText
              primary="Number of GPUS"
              secondary={job['jobParams']['resourcegpu']}
            />
          </ListItem>
        )
      }
      <ListItem>
        <ListItemText
          primary="Preemptible"
          secondary={job['jobParams']['preemptionAllowed'] ? <Check/> : <Close/>}
        />
      </ListItem>
    </List>
  );
};

export default Brief;
