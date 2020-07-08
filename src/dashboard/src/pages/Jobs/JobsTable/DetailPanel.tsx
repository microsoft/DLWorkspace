import * as React from 'react'
import {
  FunctionComponent,
} from 'react'
import {
  List,
  ListItem,
  ListItemText
} from '@material-ui/core'
import { get } from 'lodash'

import CopyableTextListItem from '../../../components/CopyableTextListItem'

import { Job } from '../utils'

interface Props {
  job: Job;
}

const DetailPanel: FunctionComponent<Props> = ({ job }) => {
  const submitted = new Date(get(job, 'jobTime'))
  const started = new Date(get(job, 'jobStatusDetail.0.startedAt'))
  const finished = new Date(get(job, 'jobStatusDetail.0.finishedAt'))

  return (
    <List dense disablePadding>
      <CopyableTextListItem
        primary="Job Id"
        secondary={job['jobId']}
      />
      <CopyableTextListItem
        primary="Job Name"
        secondary={job['jobName']}
      />
      { isFinite(submitted.valueOf()) && (
        <ListItem>
          <ListItemText
            primary="Job Submitted Time"
            secondary={submitted.toLocaleString()}
          />
        </ListItem>
      ) }
      { isFinite(started.valueOf()) && (
        <ListItem>
          <ListItemText
            primary="Job Started Time"
            secondary={started.toLocaleString()}
          />
        </ListItem>
      ) }
      { isFinite(finished.valueOf()) && (
        <ListItem>
          <ListItemText
            primary="Job Finished Time"
            secondary={finished.toLocaleString()}
          />
        </ListItem>
      ) }
    </List>
  )
}

export default DetailPanel
