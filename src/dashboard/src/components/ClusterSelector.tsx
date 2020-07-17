import * as React from 'react'
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from 'react'

import {
  MenuItem,
  Select
} from '@material-ui/core'
import { SelectProps } from '@material-ui/core/Select'

import ClustersContext from '../contexts/Clusters'

interface ClusterSelectorProps extends Omit<SelectProps, 'value' | 'onChange'> {
  defaultId?: string
  onChange?: (cluster: { id: string }) => void
}

const ClusterSelector: FunctionComponent<ClusterSelectorProps> = ({ defaultId: defaultClusterId, onChange, ...props }) => {
  const { clusters } = useContext(ClustersContext)
  const [clusterId, setClusterId] = useState(defaultClusterId)
  const cluster = useMemo(() => {
    if (clusterId === undefined) return undefined

    return clusters.filter((cluster) => cluster.id === clusterId)[0]
  }, [clusters, clusterId])
  const setCluster = useCallback((cluster: any) => {
    setClusterId(cluster.id)
    if (onChange !== undefined) onChange(cluster)
  }, [setClusterId, onChange])
  const onSelectChange = useCallback((event: ChangeEvent<{ value: any }>) => {
    if (event.target.value == null) return

    setCluster(event.target.value)
  }, [setCluster])
  useEffect(() => {
    if (clusters.length === 0) return
    if (cluster !== undefined) return

    const defaultCluster = clusters[0]
    setCluster(defaultCluster)
  }, [clusters, cluster, setCluster])

  if (clusters.length === 0) return null
  if (cluster === undefined) return null

  return (
    <Select value={cluster} onChange={onSelectChange} {...props}>
      {
        clusters.map((cluster) => (
          <MenuItem key={cluster.id} value={cluster}>
            {cluster.id}
          </MenuItem>
        ))
      }
    </Select>
  )
}

export default ClusterSelector
