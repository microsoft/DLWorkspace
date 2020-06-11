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

import { clamp, each, map, set, sortBy } from 'lodash';

import {
  Box,
  MenuItem,
  Select,
  createStyles,
  colors,
  makeStyles,
} from '@material-ui/core';

import {
  PieChart,
  Pie,
  ResponsiveContainer,
  Cell,
  LabelList
} from 'recharts';

import { Column, Options } from 'material-table';

import Loading from '../../components/Loading';
import SvgIconsMaterialTable from '../../components/SvgIconsMaterialTable';
import TeamContext from '../../contexts/Team';
import usePrometheus from '../../hooks/usePrometheus';
import useTableData from '../../hooks/useTableData';
import { formatBytes } from '../../utils/formats';

const useLabelStyle = makeStyles((theme) => createStyles({
  root: {
    fill: theme.palette.text.primary,
    stroke: "transparent"
  }
}))

const getPieColor = (ratio: number) => colors.red[
  clamp(Math.floor(ratio * 10), .5, 9) * 100 as keyof typeof colors.red
];

interface StoragesContentProps {
  data: {
    mountpoint: string;
    data: {
      user: string;
      bytes: number;
      ratio: number;
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
  }).current;

  const labelStyle = useLabelStyle();

  const valueAccessor = useCallback(({ percent, payload }) => {
    if (percent < 0.05) return null;
    return payload.user;
  }, []);

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

    return sortBy(map(mountpointUserBytes, (userBytes, mountpoint) => {
      let sum = 0;

      const data = sortBy(map(userBytes, (bytes: number, user) => {
        sum += bytes;
        return { user, bytes, ratio: 0 };
      }), 'bytes').reverse()

      each(data, (obj) => { obj.ratio = obj.bytes / sum });

      return { mountpoint, data }
    }), 'mountpoint')
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
