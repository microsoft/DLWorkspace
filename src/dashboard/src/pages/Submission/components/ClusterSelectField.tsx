import * as React from 'react'

import { MenuItem, TextField } from '@material-ui/core'
import { BaseTextFieldProps } from '@material-ui/core/TextField'

import ClustersContext from '../../../contexts/Clusters'
import TeamContext from '../../../contexts/Team'
import useFetch from 'use-http'
import * as _ from 'lodash'
import { sumValues } from '../../../utlities/ObjUtlities'

interface ClusterSelectFieldProps {
  cluster: string | undefined
  onClusterChange(value: string): void
}

const ClusterSelectField: React.FC<ClusterSelectFieldProps & BaseTextFieldProps> = (
  { cluster, onClusterChange, variant = 'standard', ...props }
) => {
  const { clusters } = React.useContext(ClustersContext)
  const { currentTeamId } = React.useContext(TeamContext)
  const fetchVcStatusUrl = '/api'
  const [helperText, setHelperText] = React.useState('')

  const request = useFetch(fetchVcStatusUrl)
  const fetchVC = async () => {
    const response = await request.get(`/teams/${currentTeamId}/clusters/${cluster}`)
    return response
  }
  const onChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      onClusterChange(event.target.value)
    },
    [onClusterChange]
  )
  const isEmpty = (obj: object) => {
    if (obj === undefined) return true
    for (const key in obj) {
      if (obj.hasOwnProperty(key))
        return false
    }
    return true
  }
  React.useEffect(() => {
    fetchVC().then((res) => {
      let clusterName = ''
      if (!isEmpty(res)) {
        clusterName = (String)(Object.keys(res['gpu_capacity'])[0])
      }
      if (clusterName === 'undefined') {
        clusterName = (String)(Object.keys(res['cpu_capacity'])[0])
      }
      const gpuCapacity = isEmpty(res) ? 0 : (String)(sumValues(res['gpu_capacity']))
      const gpuAvailable = isEmpty(res) ? 0 : (String)(sumValues(res['gpu_avaliable']))
      if (isEmpty(res['gpu_capacity'])) {
        setHelperText(`${clusterName}`)
      } else {
        setHelperText(`${clusterName} (${gpuAvailable} / ${gpuCapacity} to use)`)
      }
    })
    if (cluster) {
      onClusterChange(cluster)
    }
  }, [clusters, onClusterChange, cluster])

  if (cluster === undefined) {
    return null
  }

  return (
    <TextField
      select
      label="Cluster"
      helperText={helperText}
      variant="filled"
      {...props}
      value={cluster}
      onChange={onChange}
    >
      {// const filterclusters = clusters.filter((cluster)=>(boolean)cluster["admin"]);
        clusters && _.map(clusters, 'id').map(cluster => (
          <MenuItem key={cluster} value={cluster}>{cluster}</MenuItem>
        ))
      }
    </TextField>
  )
}

export default ClusterSelectField
