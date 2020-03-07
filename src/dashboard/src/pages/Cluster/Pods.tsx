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
  Tooltip
} from '@material-ui/core';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import useTableData from '../../hooks/useTableData';
import TeamsContext from '../../contexts/Teams';

import { humanBytes } from '../Clusters/useResourceColumns';
import usePrometheus from '../../hooks/usePrometheus';

interface Props {
  clusterConfig: any;
  workers: any;
  query?: string;
}

const Pods: FunctionComponent<Props> = ({ clusterConfig, workers, query }) => {
  const { clusterId } = useParams();
  const { selectedTeam } = useContext(TeamsContext);

  const gpuUtilizationMetrics = usePrometheus(clusterConfig, `avg(task_gpu_percent {vc_name="${selectedTeam}"}) by (pod_name)`);
  const gpuIdleMetrics = usePrometheus(clusterConfig, `count(task_gpu_percent {vc_name="${selectedTeam}"} == 0) by (pod_name)`);

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
        <UILink variant="subtitle2" component={RouterLink} to={`/jobs-v2/${clusterId}/${jobId}`}>
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
    title: 'GPU Utilization',
    field: 'gpuMetrics.utilization',
    type: 'numeric',
    render: ({ gpuMetrics }) => gpuMetrics && <>{Number(gpuMetrics.utilization).toPrecision(2)}%</>
  } as Column<any>, {
    title: 'GPU Idle',
    field: 'gpuMetrics.idle',
    type: 'numeric',
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
    />
  );
};

export default Pods;
