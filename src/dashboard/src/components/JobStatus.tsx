import * as React from 'react'
import { ReactElement, FunctionComponent, useMemo, useEffect } from 'react'
import { capitalize, noop } from 'lodash'
import {
  // colors,
  // createMuiTheme,
  Chip,
  Tooltip
} from '@material-ui/core'
import {
  HourglassEmpty,
  HourglassFull,
  CheckCircleOutline,
  ErrorOutline,
  PauseCircleFilled,
  PauseCircleOutline,
  RemoveCircle,
  RemoveCircleOutline,
  Help,
  More
} from '@material-ui/icons'
// import {
//   ThemeProvider,
// } from '@material-ui/styles';

import useFetch from 'use-http-1'

interface Props {
  cluster: string
  job: any
}

const JobStatus: FunctionComponent<Props> = ({ cluster, job }) => {
  const id = useMemo<string>(() => job['jobId'], [job])
  const status = useMemo<string>(() => job['jobStatus'], [job])
  const icon = useMemo(() =>
    status === 'unapproved' ? <HourglassEmpty/>
      : status === 'queued' ? <HourglassEmpty/>
        : status === 'scheduling' ? <HourglassEmpty/>
          : status === 'running' ? <HourglassFull/>
            : status === 'finished' ? <CheckCircleOutline/>
              : status === 'failed' ? <ErrorOutline/>
                : status === 'pausing' ? <PauseCircleFilled/>
                  : status === 'paused' ? <PauseCircleOutline/>
                    : status === 'killing' ? <RemoveCircle/>
                      : status === 'killed' ? <RemoveCircleOutline/>
                        : <Help/>
  , [status])
  // const theme = useMemo(() => createMuiTheme({
  //   palette: {
  //     primary: status === 'unapproved' ? colors.blueGrey
  //       : status === 'queued' ? colors.blueGrey
  //       : status === 'scheduling' ? colors.blueGrey
  //       : status === 'running' ? undefined
  //       : status === 'finished' ? colors.green
  //       : status === 'failed' ? colors.red
  //       : status === 'pausing' ? colors.yellow
  //       : status === 'paused' ? colors.yellow
  //       : status === 'killing' ? colors.red
  //       : status === 'killed' ? colors.red
  //       : colors.blueGrey
  //   }
  // }), [status]);
  const label = useMemo(() => capitalize(status), [status])

  const { data: statusData, get, abort } = useFetch(
    `/api/clusters/${cluster}/jobs/${id}/status`)

  const detail = useMemo<any[]>(() => job['jobStatusDetail'], [job])
  const title = useMemo(() => {
    if (statusData && statusData.message) return statusData.message
    if (!Array.isArray(detail)) return null
    if (detail.length === 0) return null
    const firstDetail = detail[0]
    if (typeof firstDetail !== 'object') return null
    const firstDetailMessage = firstDetail.message
    if (typeof firstDetailMessage === 'string') return firstDetailMessage
    if (typeof firstDetailMessage === 'object') {
      return (
        <pre>{JSON.stringify(firstDetailMessage, null, 2)}</pre>
      )
    }
    return <pre>{JSON.stringify(firstDetail, null, 2)}</pre>
  }, [statusData, detail])

  useEffect(() => {
    if (status === 'failed' || status === 'killed') {
      get()
      return abort
    }
  }, [id, status, get, abort])

  let deleteIcon: ReactElement | undefined
  if (title) {
    deleteIcon = (
      <Tooltip title={title} placement="right" interactive>
        <More/>
      </Tooltip>
    )
  }
  return (
    <Chip
      icon={icon}
      label={label}
      deleteIcon={deleteIcon}
      onDelete={deleteIcon && noop}
    />
  )
}

export default JobStatus
