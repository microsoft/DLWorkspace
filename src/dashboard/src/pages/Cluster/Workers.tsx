import React, {
  FunctionComponent,
  useCallback,
  useContext,
  useMemo,
  useRef
} from 'react';
import {
  each,
  find,
  map,
  mapValues
} from 'lodash';
import {
  Link,
  Tooltip,
  Typography
} from '@material-ui/core';
import {
  Favorite
} from '@material-ui/icons';
import MaterialTable, {
  Column,
  Options
} from 'material-table';

import TeamsContext from '../../contexts/Teams';
import useTableData from '../../hooks/useTableData';
import usePrometheus from '../../hooks/usePrometheus';

import useResourceColumns, { ResourceKind } from '../Clusters/useResourceColumns';

interface Props {
  clusterConfig: any;
  types: any;
  workers: any;
  onSearchPods: (query: string) => void;
}

const Workers: FunctionComponent<Props> = ({ clusterConfig, types, workers, onSearchPods }) => {
  const { selectedTeam } = useContext(TeamsContext);
  const metrics = usePrometheus(clusterConfig, `avg(task_gpu_percent{vc_name="${selectedTeam}"}) by (instance)`);
  const workersGPUUtilization = useMemo(() => {
    const workersGPUUtilization: { [workerName: string]: number } = Object.create(null);
    if (metrics) {
      for (const { metric, value } of metrics.result) {
        const instanceIP = metric.instance.split(':', 1)[0];
        workersGPUUtilization[instanceIP] = value[1];
      }
    }
    return workersGPUUtilization;
  }, [metrics])

  const data = useMemo(() => {
    const typesData = map(types, (status, id) => ({ id, status }));
    const workersData = map(workers, (worker, id) => ({ id, ...worker }));
    each(workersData, (workerData) => {
      workerData.status = mapValues(workerData.status, (value) => {
        return {
          ...value,
          unschedulable: (value.total || 0) - (value.allocatable || 0),
          available: (value.allocatable || 0) - (value.used || 0)
        }
      });
      workerData.gpuUtilization = workersGPUUtilization[workerData.ip];
    })
    return typesData.concat(workersData)
  }, [types, workers, workersGPUUtilization]);
  const tableData = useTableData(data, { isTreeExpanded: true });

  const handleWorkerClick = useCallback((workerName: string) => () => {
    onSearchPods(workerName);
  }, [onSearchPods]);

  const resourceKinds = useRef<ResourceKind[]>(
    ['total', 'unschedulable', 'used', 'preemptable', 'available']
  ).current;
  const resourceColumns = useResourceColumns(resourceKinds);
  const columns = useMemo(() => {
    const columns: Column<any>[] = [{
      field: 'id',
      render: ({ id, healthy }) => {
        if (typeof healthy === 'boolean') {
          return (
            <Tooltip title={`Show Pods on ${id}`}>
              <Link
                component="button"
                variant="subtitle2"
                style={{ textAlign: 'left' }}
                onClick={handleWorkerClick(id)}
              >
                <>
                  { healthy || <Favorite color="error" fontSize="inherit"/> }
                  {id}
                </>
              </Link>
            </Tooltip>
          );
        } else {
          return <Typography variant="subtitle2">{id}</Typography>;
        }
      }
    }];
    columns.push(...resourceColumns);
    columns.push({
      title: 'GPU Utilization',
      field: 'gpuUtilization',
      type: 'numeric',
      render: ({ gpuUtilization }) => gpuUtilization && <>{Number(gpuUtilization).toPrecision(2)}%</>
    });
    return columns;
  }, [resourceColumns, handleWorkerClick]);

  const options = useRef<Options>({
    padding: 'dense',
    toolbar: false,
    draggable: false,
    paging: false,
    detailPanelColumnAlignment: 'right'
  }).current;

  const parentChildData = useCallback(({ type }, rows: any[]) => {
    return find(rows, ({ id }) => type === id);
  }, []);

  return (
    <MaterialTable
      data={tableData}
      columns={columns}
      options={options}
      parentChildData={parentChildData}
    />
  );
};

export default Workers;
