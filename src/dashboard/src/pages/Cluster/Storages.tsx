import * as React from 'react'
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react'

import { clamp, each, map, set, sortBy } from 'lodash'

import {
  Box,
  MenuItem,
  Select,
  Typography,
  createStyles,
  colors,
  makeStyles
} from '@material-ui/core'

import {
  PieChart,
  Pie,
  ResponsiveContainer,
  Cell,
  LabelList
} from 'recharts'

import { Column, Options } from 'material-table'

import Loading from '../../components/Loading'
import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable'
import TeamContext from '../../contexts/Team'
import usePrometheus from '../../hooks/usePrometheus'
import useTableData from '../../hooks/useTableData'
import { formatBytes } from '../../utils/formats'

const useLabelStyle = makeStyles((theme) => createStyles({
  root: {
    fill: theme.palette.text.primary,
    stroke: 'transparent'
  }
}))

const getPieColor = (ratio: number) => colors.red[
  clamp(Math.floor(ratio * 10), .5, 9) * 100 as keyof typeof colors.red
]

interface StoragesContentProps {
  data: Array<{
    mountpoint: string
    data: Array<{
      user: string
      bytes: number
      ratio: number
    }>
  }>
  snapshot: Date
}

const StoragesContent: FunctionComponent<StoragesContentProps> = ({ data, snapshot }) => {
  const [index, setIndex] = useState(0)
  const { data: mountpoint } = data[index]

  const handleSelectChange = useCallback((event: ChangeEvent<{ value: unknown }>) => {
    setIndex(event.target.value as number)
  }, [])

  const tableData = useTableData(mountpoint)
  const columns = useRef<Array<Column<{
    user: string
    bytes: number
  }>>>([{
    field: 'user',
    title: 'User'
  }, {
    field: 'bytes',
    title: 'Storage Used',
    render ({ bytes }) { return formatBytes(bytes) }
  }]).current
  const options = useMemo<Options>(() => ({
    padding: 'dense',
    search: false,
    paging: false,
    draggable: false,
    exportButton: true,
    exportFileName: `Storage@${snapshot.toISOString()}`
  }), [snapshot])

  const labelStyle = useLabelStyle()

  const valueAccessor = useCallback(({ percent, payload }) => {
    if (percent < 0.05) return null
    return payload.user
  }, [])

  return (
    <Box display="flex" alignItems="stretch">
      <SvgIconsMaterialTable
        style={{ flex: 1 }}
        title={
          <Box display="flex" alignItems="baseline">
            <Select value={index} onChange={handleSelectChange}>
              {data.map(({ mountpoint }, index) => (
                <MenuItem key={index} value={index}>
                  {mountpoint}
                </MenuItem>
              ))}
            </Select>
            <Typography variant="caption" component={Box} paddingLeft={1}>
              Snapshot at {snapshot.toLocaleString()}
            </Typography>
          </Box>
        }
        data={tableData}
        columns={columns}
        options={options}
      />
      <ResponsiveContainer aspect={1} width={360}>
        <PieChart>
          <Pie
            data={mountpoint}
            nameKey="user"
            dataKey="bytes"
            isAnimationActive={false}
            outerRadius={100}
          >
            {
              map(mountpoint, ({ ratio }, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={getPieColor(ratio)}
                />
              ))
            }
            <LabelList
              position="outside"
              valueAccessor={valueAccessor}
              className={labelStyle.root}
            />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </Box>
  )
}

interface Props {
  data: any
}

const Storages: FunctionComponent<Props> = ({ data: { config } }) => {
  const { currentTeamId } = useContext(TeamContext)
  const metrics = usePrometheus(config['grafana'], `storage_usage_in_bytes_by_user{vc="${currentTeamId}"} or storage_usage_in_bytes_by_user{vc="cluster"}`)

  const [data, snapshot] = useMemo(() => {
    if (metrics == null || metrics.result == null) return [undefined, 0] as const

    const mountpointUserBytes = Object.create(null)
    let latestSnapshot = 0
    for (const { metric, value } of metrics.result) {
      const { mountpoint, user, snapshot_time: snapshot } = metric
      const bytes = Number(value[1])

      if (!bytes) continue

      set(mountpointUserBytes, [mountpoint, user], bytes)
      if (latestSnapshot < snapshot) {
        latestSnapshot = snapshot
      }
    }

    return [sortBy(map(mountpointUserBytes, (userBytes, mountpoint) => {
      let sum = 0

      const data = sortBy(map(userBytes, (bytes: number, user) => {
        sum += bytes
        return { user, bytes, ratio: 0 }
      }), 'bytes').reverse()

      each(data, (obj) => { obj.ratio = obj.bytes / sum })

      return { mountpoint, data }
    }), 'mountpoint'), latestSnapshot] as const
  }, [metrics])

  if (data === undefined) {
    return <Loading>Fetching Storage Metrics</Loading>
  }

  if (data.length === 0) {
    return null
  }

  return <StoragesContent data={data} snapshot={new Date(snapshot * 1000)}/>
}

export default Storages
