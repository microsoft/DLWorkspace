import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from 'react';
import { useParams } from 'react-router';
import { Link as RouterLink } from 'react-router-dom';

import { filter, flatMap, map, set } from 'lodash';

import {
  Button,
  Link as UILink,
  Tooltip,
  Typography
} from '@material-ui/core';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import SortArrow from '../../components/SortArrow';
import usePrometheus from '../../hooks/usePrometheus';
import useTableData from '../../hooks/useTableData';
import TeamsContext from '../../contexts/Teams';

import { humanBytes } from '../Clusters/useResourceColumns';

interface Props {
  data: any;
  query?: string;
}

const Pods: FunctionComponent<Props> = ({ data: { config, workers }, query }) => {
  const { clusterId } = useParams();
  const { selectedTeam } = useContext(TeamsContext);

  const gpuUtilizationMetrics = usePrometheus(config['grafana'], `avg(task_gpu_percent {vc_name="${selectedTeam}"}) by (pod_name)`);
  const gpuIdleMetrics = usePrometheus(config['grafana'], `count(task_gpu_percent {vc_name="${selectedTeam}"} == 0) by (pod_name)`);

  const [filterCurrentTeam, setFilterCurrentTeam] = useState(true);

  const podsGPUMetrics = useMemo(() => {
    type GPUMetrics = { utilization: number; idle: number };
    const podsGPUMetrics: { [podName: string]: GPUMetrics } = Object.create(null);

    if (gpuUtilizationMetrics) {
      for (const { metric, value } of gpuUtilizationMetrics.result) {
        set(podsGPUMetrics, [metric['pod_name'], 'utilization'], Number(value[1]));
      }
    }
    if (gpuIdleMetrics) {
      for (const { metric, value } of gpuIdleMetrics.result) {
        set(podsGPUMetrics, [metric['pod_name'], 'idle'], Number(value[1]));
      }
    }

    return podsGPUMetrics;
  }, [gpuUtilizationMetrics, gpuIdleMetrics]);

  const pods = useMemo(() => {
    const pods = flatMap(workers, ({ pods }, workerName) =>
      map(pods, (pod, podName) =>
        ({
          id: podName,
          worker: workerName,
          gpuMetrics: podsGPUMetrics[podName],
          ...pod
        })));
    if (filterCurrentTeam) return pods;
    return filter(pods, ({ team }) => team === selectedTeam);
  }, [filterCurrentTeam, podsGPUMetrics, selectedTeam, workers]);
  const tableData = useTableData(pods);

  const handleButtonClick = useCallback(() => {
    setFilterCurrentTeam((filterCurrentTeam) => !filterCurrentTeam)
  }, []);

  const columns = useRef<Column<any>[]>([{
    field: 'id',
    render: ({ id, jobId }) => (
      <Tooltip title={`See Job ${jobId}`}>
        <UILink variant="subtitle2" component={RouterLink} to={`/jobs/${clusterId}/${jobId}`}>
          {id}
        </UILink>
      </Tooltip>
    ),
    width: 'auto'
  } as Column<any>, {
    title: 'Worker',
    field: 'worker',
    width: 'auto'
  } as Column<any>, {
    title: 'Team',
    field: 'team',
    width: 'auto'
  } as Column<any>, {
    title: 'User',
    field: 'user',
    width: 'auto'
  } as Column<any>, {
    title: 'CPU',
    field: 'cpu',
    type: 'numeric',
    width: 'auto'
  } as Column<any>, {
    title: 'GPU',
    field: 'gpu',
    type: 'numeric',
    width: 'auto'
  } as Column<any>, {
    title: 'Memory',
    field: 'memoty',
    type: 'numeric',
    render: ({ memory }) => <>{humanBytes(memory)}</>,
    width: 'auto'
  } as Column<any>, {
    title: 'Assigned GPU Utilization',
    field: 'gpuMetrics.utilization',
    type: 'numeric',
    render: ({ gpuMetrics }) => gpuMetrics && gpuMetrics.utilization && <>{Number(gpuMetrics.utilization).toFixed(2)}%</>
  } as Column<any>, {
    title: 'GPU Idle',
    field: 'gpuMetrics.idle',
    type: 'numeric',
    render: ({ gpuMetrics }) => gpuMetrics && typeof gpuMetrics.idle === 'number' && (
      <Typography variant="inherit" color={gpuMetrics.idle > 0 ? "error" : "inherit"}>
        {gpuMetrics.idle}
      </Typography>
    )
  } as Column<any>]).current;
  const options = useMemo<Options>(() => ({
    padding: "dense",
    paging: false,
    searchText: query,
  }), [query]);

  return (
    <MaterialTable
      title={
        <Button variant="outlined" onClick={handleButtonClick}>
          {filterCurrentTeam ? 'Show Pods in All Teams' : 'Show Current Team Only'}
        </Button>
      }
      data={tableData}
      columns={columns}
      options={options}
      icons={{ SortArrow }}
    />
  );
};

export default Pods;
