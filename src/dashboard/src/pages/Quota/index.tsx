import * as React from 'react'
import {
  FunctionComponent,
  useCallback,
  useEffect,
  useMemo,
  useRef
} from 'react'

import { each, get, set, sortBy } from 'lodash'

import { Helmet } from 'react-helmet'
import { useParams } from 'react-router'

import {
  Button,
  Container,
  Typography
} from '@material-ui/core'

import { Column, Options } from 'material-table'
import { useSnackbar } from 'notistack'

import useFetch from 'use-http-1'

import SvgIconMaterialTable from '../../components/SvgIconsMaterialTable'

const useQuota = (clusterId: string) => {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar()
  const { response, error, get } = useFetch(`/api/clusters/${clusterId}/quota`, [clusterId])

  useEffect(() => {
    if (error !== undefined) {
      const key = enqueueSnackbar(`Failed to fetch quota data: ${error.message}`, {
        variant: 'error',
        persist: true,
        action: <Button color="inherit" onClick={() => get()}>Retry</Button>
      })
      if (key != null) {
        return () => closeSnackbar(key)
      }
    }
  }, [error, enqueueSnackbar, get, closeSnackbar])

  return { data: response.ok ? response.data : undefined, get }
}

interface QuotaRowData {
  id: string
  types: { [type: string]: number }
}

const Quota: FunctionComponent = () => {
  const { clusterId } = useParams<{ clusterId: string }>()
  const { enqueueSnackbar } = useSnackbar()
  const { data: quota, get: getQuota } = useQuota(clusterId)
  const { response, patch } = useFetch(`/api/clusters/${clusterId}/quota`, {
    headers: { 'Content-Type': 'application/json' }
  })

  const idColumn = useRef<Column<QuotaRowData>>({
    field: 'id',
    editable: 'never',
    render: ({ id }) => (
      <Typography variant="subtitle2">
        {id}
      </Typography>
    )
  }).current

  const [data, typeGpuType, columns] = useMemo(() => {
    if (quota === undefined) {
      return [[], Object.create(null), [idColumn]]
    }
    const data: QuotaRowData[] = []
    const columns = [idColumn]
    const typeGpuType: { [typeName: string]: string | null } = Object.create(null)
    each(quota, ({ resourceQuota: quota, resourceMetadata: meta }, id) => {
      const types = Object.create(null)
      data.push({ id, types })
      each(meta.cpu, (_, type) => {
        const gpuType = get(meta, ['gpu', type, 'gpu_type'])

        typeGpuType[type] = gpuType
        types[type] = gpuType == null ? quota.cpu[type] : quota.gpu[type]
      })
    })
    each(typeGpuType, (gpuType, type) => {
      columns.push({
        field: `types.${type}`,
        type: 'numeric',
        title: `${type} (${gpuType !== null ? gpuType : 'CPU'})`
      })
    })
    return [sortBy(data, 'id'), typeGpuType, columns]
  }, [quota, idColumn])

  const options = useRef<Options>({
    actionsColumnIndex: -1,
    search: false,
    paging: false
  }).current

  const isEditable = useCallback(() => true, [])
  const handleRowUpdate = useCallback((data: QuotaRowData) => {
    const quota = Object.create(null)
    const body = {
      [data.id]: {
        resourceQuota: quota
      }
    }
    each(data.types, (value, type) => {
      const isGPU = typeGpuType[type] != null
      const number = Number(value)
      if (Number.isFinite(number)) {
        set(quota, [isGPU ? 'gpu' : 'cpu', type], number)
      }
    })
    return patch(body).then(() => {
      if (!response.ok) {
        throw Error(response.data)
      } else {
        return getQuota()
      }
    }).catch((error) => {
      enqueueSnackbar(`Failed to update quota: ${error.message}`, {
        variant: 'error'
      })
      throw error
    })
  }, [typeGpuType, patch, response, getQuota, enqueueSnackbar])

  return (
    <Container maxWidth="md">
      <Helmet title={`Quota - ${clusterId}`}/>
      <SvgIconMaterialTable
        title={`Quota - ${clusterId}`}
        isLoading={quota === undefined}
        data={data}
        columns={columns}
        editable={{ isEditable, onRowUpdate: handleRowUpdate }}
        options={options}
      />
    </Container>
  )
}

export default Quota
