import * as React from 'react';
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react';

import { map, set } from 'lodash';

import {
  Box,
  MenuItem,
  Select,
  useTheme
} from '@material-ui/core';

import {
  LabelList,
  PieChart,
  Pie,
  ResponsiveContainer,
  Cell
} from 'recharts';

import { Column, Options } from 'material-table';

import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable';
import TeamContext from '../../contexts/Team';
import usePrometheus from '../../hooks/usePrometheus';
import useTableData from '../../hooks/useTableData';
import { formatBytes } from '../../utils/formats';
import Loading from '../../components/Loading';

const compareString = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;

interface StoragesContentProps {
  data: {
    mountpoint: string;
    data: {
      user: string;
      bytes: number;
    }[];
  }[];
}

const StoragesContent: FunctionComponent<StoragesContentProps> = ({ data }) => {
  const [index, setIndex] = useState(0);
  const { data: mountpoint } = data[index];

  const handleSelectChange = useCallback((event: ChangeEvent<{ value: unknown }>) => {
    setIndex(event.target.value as number);
  }, []);

  const tableData = useTableData(mountpoint);
  const columns = useRef<Column<{
    user: string;
    bytes: number;
  }>[]>([{
    field: 'user',
    title: 'User'
  }, {
    field: 'bytes',
    title: 'Storage Used',
    render({ bytes }) { return formatBytes(bytes); }
  }]).current;
  const options = useRef<Options>({
    padding: 'dense',
    search: false,
    paging: false,
    draggable: false
  }).current

  const valueAccessor = useCallback(({ percent, user }) => {
    if (percent <= 0.01) {
      return null;
    }
    return user;
  }, []);

  const theme = useTheme();

  return (
    <Box display="flex" alignItems="stretch">
      <SvgIconsMaterialTable
        style={{ flex: 1 }}
        title={
          <Select value={index} onChange={handleSelectChange}>
            {data.map(({ mountpoint }, index) => (
              <MenuItem key={index} value={index}>
                {mountpoint}
              </MenuItem>
            ))}
          </Select>
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
          >
            {mountpoint.map(({ user }, index) => (
              <Cell
                key={user}
                fill={theme.palette.primary.dark}
              />
            ))}
            <LabelList
              position="inside"
              valueAccessor={valueAccessor}
            />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </Box>
  )
}

interface Props {
  data: any;
}

const Storages: FunctionComponent<Props> = ({ data: { config } }) => {
  const { currentTeamId } = useContext(TeamContext);
  const metrics = usePrometheus(config['grafana'], `storage_usage_in_bytes_by_user{vc="${currentTeamId}"} or storage_usage_in_bytes_by_user{vc="cluster"}`);

  const data = useMemo(() => {
    if (metrics == null || metrics.result == null) return undefined;

    const mountpointUserBytes = Object.create(null);
    for (const { metric, value } of metrics.result) {
      const { mountpoint, user } = metric;
      const bytes = Number(value[1]);

      if (!bytes) continue;

      set(mountpointUserBytes, [mountpoint, user], bytes);
    }

    return map(mountpointUserBytes,
      (userBytes, mountpoint) => ({
        mountpoint,
        data: map(userBytes,
          (bytes: number, user) => ({
            user,
            bytes
          })
        ).sort(
          ({ user: userA }, { user: userB }) => compareString(userA, userB)
        )
      })
    ).sort(
      ({ mountpoint: mountpointA }, { mountpoint: mountpointB }) => compareString(mountpointA, mountpointB)
    )
  }, [metrics]);

  if (data === undefined) {
    return <Loading>Fetching Storage Metrics</Loading>;
  }

  if (data.length === 0) {
    return null;
  }

  return <StoragesContent data={data}/>
};

export default Storages;
