import * as React from 'react'
import {useContext} from 'react'

import {
  Card,
  CardHeader,
  CardMedia,
} from '@material-ui/core'

import Context from './Context'

const Monitor: React.FC = () => {
  const { cluster, job } = useContext(Context)
  const jobStatusGrafanaUrl = `${cluster['grafana']}/dashboard/db/job-status?var-job_name=${encodeURIComponent(job['jobId'])}`

  return (
    <Card>
      <CardHeader title="Job analytics and monitoring"/>
      <CardMedia
        component="iframe"
        src={jobStatusGrafanaUrl}
        height={1080}
      />
    </Card>
  )
}

export default Monitor
