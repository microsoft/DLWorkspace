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
import {
  kebabCase,
  each,
  filter,
  map,
  mapValues,
  noop,
} from 'lodash'
import {
  Card,
  CardMedia,
  Chip,
  Link,
  MenuItem,
  Select,
  Tooltip,
  Typography,
  makeStyles
} from '@material-ui/core'
import {
  Build,
  DoneOutline,
  ErrorOutline,
  Help,
  More,
} from '@material-ui/icons'
import {
  Column,
  Options,
  DetailPanel
} from 'material-table'

import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable'
import TeamContext from '../../contexts/Team'
import useTableData from '../../hooks/useTableData'
import usePrometheus from '../../hooks/usePrometheus'

import useResourceColumns, { ResourceKind } from '../Clusters/useResourceColumns'
import QueryContext from './QueryContext'

interface WorkerStateProps {
  state: string | undefined;
  message: string | null | undefined;
}

const WorkerState: FunctionComponent<WorkerStateProps> = ({ state, message }) => {
  if (state === undefined) state = 'IN_SERVICE';
  const icon = useMemo(() =>
    state === 'IN_SERVICE' ? <DoneOutline/>
      : state === 'OUT_OF_POOL' ? <ErrorOutline/>
        : state === 'OUT_OF_POOL_UNTRACKED' ? <ErrorOutline/>
          : state === 'READY_FOR_REPAIR' ? <Build/>
            : state === 'IN_REPAIR' ? <Build/>
              : state === 'AFTER_REPAIR' ? <Build/>
                : <Help/>
  , [state])
  const label = useMemo(() => kebabCase(state), [state])
  const deleteIcon = message ? (
    <Tooltip title={message} placement="right" interactive>
      <More/>
    </Tooltip>
  ) : undefined

  return (
    <Chip
      icon={icon}
      label={label}
      deleteIcon={deleteIcon}
      onDelete={deleteIcon && noop}
      size="small"
      color={state === 'IN_SERVICE' ? 'default' : 'secondary'}
    />
  )
}

interface Props {
  data: any;
}

const useLinkStyles = makeStyles({
  button: {
    display: 'block',
    textAlign: 'left'
  }
})

const Workers: FunctionComponent<Props> = ({ data: { config, types, workers } }) => {
  const { currentTeamId } = useContext(TeamContext)
  const { setQuery } = useContext(QueryContext)

  const linkStyles = useLinkStyles()

  const [filterType, setFilterType] = useState<string>('__all__')

  const metrics = usePrometheus(config['grafana'], `avg(task_gpu_percent{vc_name="${currentTeamId}"}) by (instance)`)
  const workersGPUUtilization = useMemo(() => {
    const workersGPUUtilization: { [workerName: string]: number } = Object.create(null)
    if (metrics) {
      for (const { metric, value } of metrics.result) {
        const instanceIP = metric.instance.split(':', 1)[0]
        workersGPUUtilization[instanceIP] = value[1]
      }
    }
    return workersGPUUtilization
  }, [metrics])

  const data = useMemo(() => {
    let workersData = map(workers, (worker, id) => ({ id, ...worker }))
    if (filterType !== '__all__') {
      workersData = filter(workersData, ({ type }) => type === filterType)
    }
    each(workersData, (workerData) => {
      workerData.status = mapValues(workerData.status, (value) => {
        return {
          ...value,
          unschedulable: (value.total || 0) - (value.allocatable || 0),
          available: (value.allocatable || 0) - (value.used || 0)
        }
      })
      workerData.gpuUtilization = workersGPUUtilization[workerData.ip]
    })
    return workersData
  }, [workers, workersGPUUtilization, filterType])
  const tableData = useTableData(data)

  const handleWorkerClick = useCallback((workerName: string) => () => {
    setQuery(workerName)
  }, [setQuery])

  const resourceKinds = useRef<ResourceKind[]>(
    ['total', 'unschedulable', 'used', 'preemptable', 'available']
  ).current
  const resourceColumns = useResourceColumns(resourceKinds, config['isPureCPU'])
  const columns = useMemo(() => {
    const columns: Column<any>[] = [{
      field: 'id',
      render: ({ id, ip, state, message }) => (
        <>
          <Tooltip title={`Show Pods on ${id}`} placement="right">
            <Link
              component="button"
              variant="subtitle2"
              classes={linkStyles}
              color="inherit"
              onClick={handleWorkerClick(id)}
            >
              {id}
            </Link>
          </Tooltip>
          <Typography variant="caption" component="div">
            {ip}
          </Typography>
          <WorkerState
            state={state}
            message={message}
          />
        </>
      )
    }]
    columns.push(...resourceColumns)
    if (!config['isPureCPU']) {
      columns.push({
        title: 'GPU Utilization',
        field: 'gpuUtilization',
        type: 'numeric',
        render: ({ gpuUtilization }) => <>{Number(gpuUtilization || 0).toFixed(2)}%</>
      })
    }
    return columns
  }, [config, resourceColumns, handleWorkerClick, linkStyles])

  const options = useRef<Options>({
    padding: 'dense',
    draggable: false,
    paging: false,
    detailPanelType: 'single'
  }).current

  const handleSelectChange = useCallback((event: ChangeEvent<{ value: unknown }>) => {
    setFilterType(event.target.value as string)
  }, [])

  const detailPanel = useMemo<DetailPanel<any>[]>(() => {
    return [{
      tooltip: 'View Metrics',
      render: ({ ip }) => (
        <Card>
          <CardMedia
            component="iframe"
            src={`${config['grafana']}/dashboard/db/node-status?orgId=1&var-node=${ip}`}
            height="384"
            frameBorder="0"
          />
        </Card>
      )
    }]
  }, [config])

  return (
    <SvgIconsMaterialTable
      title={(
        <>
          Show Type: <Select value={filterType} onChange={handleSelectChange}>
            <MenuItem value="__all__">All</MenuItem>
            {map(types, (type, name) => (
              <MenuItem key={name} value={name}>{name}</MenuItem>
            ))}
          </Select>
        </>
      )}
      data={tableData}
      columns={columns}
      options={options}
      detailPanel={detailPanel}
    />
  )
}

export default Workers
