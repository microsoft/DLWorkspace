import * as React from 'react'
import {
  FunctionComponent
} from 'react'
import {
  Link
} from 'react-router-dom'

import {
  Button,
  CardActions
} from '@material-ui/core'

import { useCluster } from './Context'

const ClusterCardActions: FunctionComponent = () => {
  const { id: clusterId } = useCluster()
  return (
    <CardActions>
      <Button component={Link}
        to={{ pathname: '/submission/training-cluster', state: { cluster: clusterId } }}
        size="small" color="secondary"
      >
        Submit Training Job
      </Button>
      <Button component={Link}
        to={{ pathname: '/submission/data', state: { cluster: clusterId } }}
        size="small" color="secondary"
      >
        Submit Data Job
      </Button>
    </CardActions>
  )
}

export default ClusterCardActions
