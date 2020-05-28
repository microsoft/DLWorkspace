import * as React from 'react';
import {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react';
import { entries, find, get, keys, set, union } from 'lodash';

import {
  Button,
  Link,
  Tooltip,
  Typography
} from '@material-ui/core';
import {
  AccountBox
} from '@material-ui/icons';
import {
  Column,
  Options
} from 'material-table';

import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable';
import CaptionColumnTitle from '../../components/CaptionColumnTitle';
import TeamContext from '../../contexts/Team';
import usePrometheus from '../../hooks/usePrometheus';
import useTableData from '../../hooks/useTableData';
import { formatBytes, formatPercent, formatHours } from '../../utils/formats';

import QueryContext from './QueryContext';

const humanHours = (seconds: number) => {
  if (typeof seconds !== 'number') return seconds;
  return formatHours(seconds);
}

interface GpuMetrics {
  idle?: number;
  bookedLast31Days?: number;
  idleLast31Days?: number;
}

interface Props {
  data: any;
}

const Users: FunctionComponent<Props> = ({ data: { config, users } }) => {
  const { currentTeamId } = useContext(TeamContext);
  const { setQuery } = useContext(QueryContext);

  const [filterCurrent, setFilterCurrent] = useState(true);

  const gpuIdleMetrics = usePrometheus(config.grafana, `count (task_gpu_percent{vc_name="${currentTeamId}"} == 0) by (username)`);
  const gpuBookedLast31DaysMetrics = usePrometheus(config.grafana, `sum(job_booked_gpu_second{vc="${currentTeamId}", since="31d"}) by (user)`)
  const gpuIdleLast31DaysMetrics = usePrometheus(config.grafana, `sum(job_idle_gpu_second{vc="${currentTeamId}", since="31d"}) by (user)`)

  const handleButtonClick = useCallback(() => {
    setFilterCurrent((filterCurrent) => !filterCurrent);
  }, [setFilterCurrent]);

  const usersGPUMetrics = useMemo(() => {
    const usersGPUMetrics: { [user: string]: GpuMetrics } = Object.create(null);
    if (gpuIdleMetrics != null)  {
      for (const { metric, value } of gpuIdleMetrics.result) {
        set(usersGPUMetrics, [metric.username, 'idle'], Number(value[1]));
      }
    }
    if (gpuBookedLast31DaysMetrics != null)  {
      for (const { metric, value } of gpuBookedLast31DaysMetrics.result) {
        set(usersGPUMetrics, [metric.user, 'bookedLast31Days'], Number(value[1]));
      }
    }
    if (gpuIdleLast31DaysMetrics != null)  {
      for (const { metric, value } of gpuIdleLast31DaysMetrics.result) {
        set(usersGPUMetrics, [metric.user, 'idleLast31Days'], Number(value[1]));
      }
    }
    return usersGPUMetrics;
  }, [gpuIdleMetrics, gpuBookedLast31DaysMetrics, gpuIdleLast31DaysMetrics]);

  const data = useMemo(() => {
    const data = [];

    const totalStatus = Object.create(null);
    const total = {
      status: totalStatus,
      gpuMetrics: {
        idle: 0,
        bookedLast31Days: 0,
        idleLast31Days: 0
      },
      tableData: { isTreeExpanded: true }
    };
    data.push(total);

    const userNames = filterCurrent ? keys(users) : union(keys(users), keys(usersGPUMetrics));
    userNames.sort();

    for (const userName of userNames) {
      const userStatus = Object.create(null);
      const gpuMetrics: GpuMetrics | undefined = get(usersGPUMetrics, [userName]);
      data.push({ id: userName, status: userStatus, gpuMetrics });
      if (gpuMetrics != null) {
        const {
          idle,
          bookedLast31Days,
          idleLast31Days,
        } = gpuMetrics;
        total.gpuMetrics.idle += idle || 0;
        total.gpuMetrics.bookedLast31Days += bookedLast31Days || 0;
        total.gpuMetrics.idleLast31Days += idleLast31Days || 0;
      }

      const types = get(users, [userName, 'types']);
      for (const [typeName, status] of entries(types)) {
        data.push({ id: typeName, userName, status })
        for (const resourceType of ['cpu', 'gpu', 'memory']) {
          for (const resourceKind of ['used', 'preemptable']) {
            set(userStatus, [resourceType, resourceKind],
              get(userStatus, [resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0));
            set(totalStatus, [resourceType, resourceKind],
              get(totalStatus, [resourceType, resourceKind], 0) +
              get(status, [resourceType, resourceKind], 0));
          }
        }
      }
    }
    return data;
  }, [filterCurrent, users, usersGPUMetrics]);
  const tableData = useTableData(data);

  const handleUserClick = useCallback((userName: string) => () => {
    setQuery(userName);
  }, [setQuery]);

  const columns = useRef<Column<any>[]>([{
    field: 'id',
    render: (row) =>
      row.id === undefined
      ? <Typography variant="subtitle2">(total)</Typography>
      : row.userName
      ? <Typography variant="subtitle2">{row.id}</Typography>
      : (
        <Tooltip title={`Show ${row.id}'s Pods`}>
          <Link
            component="button"
            variant="subtitle2"
            style={{ textAlign: 'left', whiteSpace: 'nowrap' }}
            onClick={handleUserClick(row.id)}
          >
            <AccountBox fontSize="inherit"/>
            {row.id}
          </Link>
        </Tooltip>
      )
  }, {
    title: <CaptionColumnTitle caption="Used (Preemptable)">CPU</CaptionColumnTitle>,
    field: 'status.cpu.used',
    render: ({ status }) => status && (
      <>
        {get(status, ['cpu', 'used'], 0)}
        {` (${get(status, ['cpu', 'preemptable'], 0)})`}
      </>
    ),
    searchable: false,
    width: 'auto'
  } as Column<any>, {
    title: <CaptionColumnTitle caption="Used (Preemptable)">GPU</CaptionColumnTitle>,
    field: 'status.gpu.used',
    render: ({ status }) => status && (
      <>
        {get(status, ['gpu', 'used'], 0)}
        {` (${get(status, ['gpu', 'preemptable'], 0)})`}
      </>
    ),
    searchable: false,
    width: 'auto'
  } as Column<any>, {
    title: <CaptionColumnTitle caption="Used (Preemptable)">Memory</CaptionColumnTitle>,
    field: 'status.memory.used',
    render: ({ status }) => status && (
      <>
        {formatBytes(get(status, ['memory', 'used'], 0))}
        {` (${formatBytes(get(status, ['memory', 'preemptable'], 0))})`}
      </>
    ),
    searchable: false,
    width: 'auto'
  } as Column<any>, {
    title: 'GPU Idle',
    field: 'gpuMetrics.idle',
    type: 'numeric',
    render: ({ gpuMetrics }) => gpuMetrics != null && typeof gpuMetrics.idle === 'number' && (
      <Typography variant="inherit" color={gpuMetrics.idle > 0 ? "error" : "inherit"}>
        {gpuMetrics.idle}
      </Typography>
    ),
    width: 'auto'
  } as Column<any>, {
    title: <CaptionColumnTitle caption="Last 31 days">Booked GPU</CaptionColumnTitle>,
    field: 'gpuMetrics.bookedLast31Days',
    type: 'numeric',
    render: (data) => <>{humanHours(get(data, 'gpuMetrics.bookedLast31Days'))}</>,
    width: 'auto'
  } as Column<any>, {
    title: <CaptionColumnTitle caption="Last 31 days">Idle GPU (%)</CaptionColumnTitle>,
    field: 'gpu.idleLast31Days',
    type: 'numeric',
    render: (data) => {
      if (data.userName) return;

      const booked = get(data, 'gpuMetrics.bookedLast31Days', 0);
      const idle = get(data, 'gpuMetrics.idleLast31Days', 0);

      if (booked === 0) return <>{humanHours(idle)}</>;

      const percent = (idle / booked) * 100;
      if (percent > 50) {
        return (
          <>
            {humanHours(idle)}
            {" ("}
            <Typography variant="inherit" color="error">{formatPercent(percent, 1)}%</Typography>
            )
          </>
        );
      }

      return <>{humanHours(idle)}{" ("}{formatPercent(percent, 1)}%)</>;
    },
    width: 'auto'
  } as Column<any>]).current;

  const options = useRef<Options>({
    padding: 'dense',
    draggable: false,
    paging: false
  }).current;

  const parentChildData = useCallback(({ id, userName }, rows: any[]) => {
    if (id !== undefined) {
      return find(rows, ({ id }) => userName === id);
    }
  }, []);

  return (
    <SvgIconsMaterialTable
      title={
        <Button variant="outlined" onClick={handleButtonClick}>
          { filterCurrent ? "Show All Users" : "Show Current Users Only" }
        </Button>
      }
      data={tableData}
      columns={columns}
      options={options}
      parentChildData={parentChildData}
    />
  )
};

export default Users;
