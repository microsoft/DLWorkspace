import * as React from 'react'
import {
  FunctionComponent,
  FocusEvent,
  KeyboardEvent,
  useCallback,
  useContext,
  useMemo,
  useState,
  useRef
} from 'react'

import { get, isEqual, isFinite, noop } from 'lodash'

import {
  Input,
  InputAdornment,
  Typography
} from '@material-ui/core'
import { Column } from 'material-table'
import { useSnackbar } from 'notistack'

import ClusterContext from '../../ClusterContext'
import { Job } from '../../../../utils/jobs'

interface TimeoutFieldProps {
  job: any
}

const EDITABLE_STATUSES = new Set([
  'running',
  'queued',
  'scheduling',
  'unapproved',
  'paused',
  'pausing'
])

const TimeoutField: FunctionComponent<TimeoutFieldProps> = ({ job }) => {
  const { enqueueSnackbar } = useSnackbar()
  const { cluster } = useContext(ClusterContext)
  const [busy, setBusy] = useState(false)
  const input = useRef<HTMLInputElement>()
  const editable = useMemo(() => {
    return EDITABLE_STATUSES.has(job['jobStatus'])
  }, [job])
  const defaultHours = useMemo<number>(() => {
    const seconds = get(job, ['jobParams', 'maxTimeSec'])
    return seconds != null ? seconds / 60 / 60 : NaN
  }, [job])
  const setHours = useCallback((hours: number) => {
    if (isEqual(hours, defaultHours)) return
    enqueueSnackbar('Timeout is being set...')
    setBusy(true)

    fetch(`/api/clusters/${cluster.id}/jobs/${job['jobId']}/timeout`, {
      method: 'PUT',
      body: JSON.stringify({ timeout: isFinite(hours) ? hours * 60 * 60 : null }),
      headers: { 'Content-Type': 'application/json' }
    }).then((response) => {
      if (response.ok) {
        enqueueSnackbar('Timeout is set successfully', { variant: 'success' })
      } else {
        throw Error()
      }
    }).catch(() => {
      enqueueSnackbar('Failed to set timeout', { variant: 'error' })
    }).then(() => {
      setBusy(false)
    }, noop)
  }, [defaultHours, enqueueSnackbar, job, cluster.id])
  const onBlur = useCallback((event: FocusEvent<HTMLInputElement>) => {
    if (input.current === undefined) return
    setHours(input.current.valueAsNumber)
  }, [setHours])
  const onKeyDown = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    if (input.current === undefined) return
    if (event.key === 'Enter') {
      setHours(input.current.valueAsNumber)
    }
    if (event.key === 'Escape') {
      if (isFinite(defaultHours)) {
        input.current.valueAsNumber = defaultHours
      } else {
        input.current.value = ''
      }
      input.current.blur()
    }
  }, [setHours, defaultHours])

  if (editable) {
    return (
      <Input
        inputRef={input}
        type="number"
        placeholder="N/A"
        endAdornment={<InputAdornment position="end">h</InputAdornment>}
        defaultValue={isFinite(defaultHours) ? String(defaultHours) : ''}
        disabled={busy}
        fullWidth
        style={{ color: 'inherit', fontSize: 'inherit' }}
        inputProps={{
          style: {
            color: 'inherit',
            fontSize: 'inherit',
            textAlign: 'right'
          },
          onBlur
        }}
        onKeyDown={onKeyDown}
      />
    )
  } else {
    if (isFinite(defaultHours)) {
      return <>{defaultHours} h</>
    } else {
      return <Typography variant="inherit" color="textSecondary">N/A</Typography>
    }
  }
}

const valueOf = (job: Job): number => {
  return get(job, ['jobParams', 'maxTimeSec'], NaN)
}

export default (): Column<Job> => ({
  title: 'Timeout',
  type: 'numeric',
  render (job) {
    return <TimeoutField job={job}/>
  },
  customSort (job1, job2) {
    return valueOf(job1) - valueOf(job2)
  }
})
