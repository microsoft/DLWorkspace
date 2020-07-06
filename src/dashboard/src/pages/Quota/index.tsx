import * as React from 'react';
import {
  ChangeEvent,
  FunctionComponent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { assign, each, map, set } from 'lodash';

import { Helmet } from 'react-helmet';
import { useParams } from 'react-router';

import {
  Button,
  Container,
  TextField,
  InputAdornment,
  Link,
} from '@material-ui/core';

import { Column, Options } from 'material-table';
import { useSnackbar } from 'notistack';

import useFetch from 'use-http-1';

import Loading from '../../components/Loading';
import SvgIconMaterialTable from '../../components/SvgIconsMaterialTable';
import { formatBytes } from '../../utils/formats'

interface BytesTextFieldProps {
  value: number;
  onChange: (newValue: number) => void;
}

const BytesTextField: FunctionComponent<BytesTextFieldProps> = ({ value, onChange }) => {
  const [unit, setUnit] = useState<'B' | 'KiB' | 'MiB' | 'GiB' | 'TiB'>('B');
  const multiplier = useMemo(() => ({
    B: 1,
    KiB: 1024,
    MiB: 1024 * 1024,
    GiB: 1024 * 1024 * 1024,
    TiB: 1024 * 1024 * 1024 * 1024,
  })[unit] || 1, [unit])

  const handleChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    onChange(Math.round(event.target.valueAsNumber * multiplier));
  }, [onChange, multiplier]);

  const handleClick = useCallback(() => {
    setUnit((unit) => (
      unit === 'B' ? 'KiB' :
      unit === 'KiB' ? 'MiB' :
      unit === 'MiB' ? 'GiB' :
      unit === 'GiB' ? 'TiB' : 'B'
    ));
  }, [setUnit]);

  return (
    <TextField
      type="number"
      value={value / multiplier}
      fullWidth
      onChange={handleChange}
      InputProps={{
        style: {fontSize: 13},
        endAdornment: (
          <InputAdornment position="end">
            <Link component="button" underline="none" onClick={handleClick}>
              {unit}
            </Link>
          </InputAdornment>
        )
      }}
    />
  );
};

interface QuotaData {
  [skuType: string]: {
    [teamId: string]: {
      gpu: number;
      cpu: number;
      memory: number;
      gpuMemory: number;
    };
  };
}

interface QuotaRowData {
  id: string;
  gpu: number;
  cpu: number;
  memory: number;
  gpuMemory: number;
}

const Quota: FunctionComponent = () => {
  const { clusterId } = useParams<{ clusterId: string }>();
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { data: quota, error, get: retry } = useFetch(`/api/clusters/${clusterId}/quota`, [clusterId]);
  const { response, patch } = useFetch(`/api/clusters/${clusterId}/quota`, {
    headers: {
      'Content-Type': 'application/json'
    }
  });

  const data = useMemo<QuotaData | undefined>(() => {
    if (quota === undefined) return undefined;
    const data: QuotaData = Object.create(null)
    each(quota, ({ resourceQuota: quota }, id) => {
      each(quota.gpu, (value, type) => {
        set(data, [type, id, 'gpu'], value)
      })
      each(quota.cpu, (value, type) => {
        set(data, [type, id, 'cpu'], value)
      })
      each(quota.memory, (value, type) => {
        set(data, [type, id, 'memory'], value)
      })
      each(quota['gpu_memory'], (value, type) => {
        set(data, [type, id, 'gpuMemory'], value)
      })
    });
    return data;
  }, [quota]);


  const columns = useRef<Column<QuotaRowData>[]>([{
    field: 'id',
    editable: 'never',
    render: ({ id }) => <strong>{id}</strong>,
  },{
    field: 'gpu',
    type: 'numeric',
    title: 'GPU',
  },{
    field: 'cpu',
    type: 'numeric',
    title: 'CPU',
  },{
    field: 'memory',
    type: 'numeric',
    render: ({ memory }) => <>{formatBytes(memory)}</>,
    editComponent: (props) => <BytesTextField {...props}/>,
    title: 'Memory',
  },{
    field: 'gpuMemory',
    type: 'numeric',
    render: ({ gpuMemory }) => <>{formatBytes(gpuMemory)}</>,
    editComponent: (props) => <BytesTextField {...props}/>,
    title: 'GPU Memory',
  }]).current;
  const options = useRef<Options>({
    actionsColumnIndex: -1,
    search: false,
    paging: false,
  }).current;

  const isEditable = useCallback(() => true, []);
  const handleRowUpdate = useCallback((type: string) => (data: QuotaRowData) => {
    const body = {
      [data.id]: {
        resourceQuota: {
          gpu: {
            [type]: Number(data.gpu) || undefined,
          },
          cpu: {
            [type]: Number(data.cpu) || undefined,
          },
          memory: {
            [type]: Number(data.memory) || undefined,
          },
          'gpu_memory': {
            [type]: Number(data.gpuMemory) || undefined,
          },
        }
      }
    }
    return patch(body).then(() => {
      if (!response.ok) {
        throw Error(response.data);
      } else {
        return retry()
      }
    }).catch((error) => {
      enqueueSnackbar(`Failed to update quota: ${error.message}`, {
        variant: 'error'
      });
      throw error;
    })
  }, [patch, retry, response, enqueueSnackbar]);

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch quota data: ${error.message}`, {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={() => retry()}>Retry</Button>,
      })
      if (key != null) {
        return () => closeSnackbar(key);
      }
    }
  }, [error, enqueueSnackbar, retry, closeSnackbar]);

  if (data === undefined) {
    return <Loading>Fetching Resource Quota</Loading>;
  }

  return (
    <Container>
      <Helmet title={`${clusterId} Resource Quota`}/>
      {map(data, (data, type) => (
        <SvgIconMaterialTable
          key={type}
          data={map(data, (quota, id) => assign({ id }, quota))}
          columns={columns}
          editable={{ isEditable, onRowUpdate: handleRowUpdate(type) }}
          options={options}
          title={`${clusterId} / ${type}`}
        />
      ))}
    </Container>
  );
};

export default Quota;
