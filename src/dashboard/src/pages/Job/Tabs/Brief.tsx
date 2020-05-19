import * as React from 'react';
import {
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
  Group,
  Remove
} from '@material-ui/icons';
import { get } from 'lodash';

import CodeBlock from '../../../components/CodeBlock';
import CopyableTextListItem from '../../../components/CopyableTextListItem';

import useRouteParams from '../useRouteParams';
import Context from '../Context';

const Brief: FunctionComponent = () => {
  const { clusterId, jobId } = useRouteParams();
  const { cluster, job } = useContext(Context);

  const submitted = new Date(get(job, 'jobTime'));
  const started = new Date(get(job, 'jobStatusDetail.0.startedAt'));
  const finished = new Date(get(job, 'jobStatusDetail.0.finishedAt'));
  return (
    <List dense disablePadding>
      <CopyableTextListItem primary="Job Id" secondary={jobId}/>
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
      { isFinite(submitted.valueOf()) && (
        <ListItem>
          <ListItemText primary="Job Submitted Time" secondary={submitted.toLocaleString()}/>
        </ListItem>
      ) }
      { isFinite(started.valueOf()) && (
        <ListItem>
          <ListItemText primary="Job Started Time" secondary={started.toLocaleString()}/>
        </ListItem>
      ) }
      { isFinite(finished.valueOf()) && (
        <ListItem>
          <ListItemText primary="Job Finished Time" secondary={finished.toLocaleString()}/>
        </ListItem>
      ) }
      <Divider />
      <ListItem>
        <ListItemText primary="Job Type" secondary={get(job, 'jobParams.jobtrainingtype')}/>
      </ListItem>
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
          secondary={job['jobParams']['preemptionAllowed'] ? <Check/> : <Remove/>}
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
        <ListItemText primary="Docker Image" secondary={job['jobParams']['image']}/>
      </ListItem>
      <ListItem>
        <ListItemText
          primary="Command"
          secondary={<CodeBlock>{job['jobParams']['cmd']}</CodeBlock>}
          secondaryTypographyProps={{ component: 'div' }}
        />
      </ListItem>
    </List>
  );
};

Brief.displayName = 'Brief';

export default Brief;
