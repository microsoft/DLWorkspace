import React, {
  FunctionComponent,
  useContext
} from 'react';
import {
  Divider,
  List,
  ListItem,
  ListItemText
} from '@material-ui/core';
import {
  Check,
  Close
} from '@material-ui/icons';

import CopyableTextListItem from '../../../components/CopyableTextListItem';

import useRouteParams from '../useRouteParams';
import Context from '../Context';

const Brief: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { cluster, job } = useContext(Context);

  return (
    <List dense>
      <ListItem>
        <ListItemText primary="Job Id" secondary={jobId}/>
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
          secondary={job['jobParams']['cmd']}
          secondaryTypographyProps={{ component: 'pre' }}
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
        <ListItemText primary="Team Name" secondary={job['vcName']}/>
      </ListItem>
      <ListItem>
        <ListItemText primary="Email" secondary={job['userName']}/>
      </ListItem>
      <Divider />
      <ListItem>
        <ListItemText
          primary="Cluster"
          secondary={clusterId}
        />
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Preemptible"
          secondary={job['jobParams']['preemptionAllowed'] ? <Check/> : <Close/>}
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
    </List>
  );
};

export default Brief;
