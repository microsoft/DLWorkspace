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

import { Input } from '@material-ui/core'
import { Column } from 'material-table'
import { useSnackbar } from 'notistack'

import ClusterContext from '../../ClusterContext'
import { Job } from '../../utils'

const DEFAULT_PRIORITY = 100

interface PriorityFieldProps {
  job: any;
}

const EDITABLE_STATUSES = new Set([
  'running',
  'queued',
  'scheduling',
  'unapproved',
  'paused',
  'pausing'
])

const PriorityField: FunctionComponent<PriorityFieldProps> = ({ job }) => {
  const { enqueueSnackbar } = useSnackbar()
  const { cluster } = useContext(ClusterContext)
  const [busy, setBusy] = useState(false)
  const input = useRef<HTMLInputElement>()
  const editable = useMemo(() => {
    return EDITABLE_STATUSES.has(job['jobStatus'])
  }, [job])
  const priority = useMemo(() => {
    if (job['priority'] == null) {
      return DEFAULT_PRIORITY
    }
    return job['priority']
  }, [job])
  const setPriority = useCallback((priority: number) => {
    if (priority === job['priority']) return
    enqueueSnackbar('Priority is being set...')
    setBusy(true)

    fetch(`/api/clusters/${cluster.id}/jobs/${job['jobId']}/priority`, {
      method: 'PUT',
      body: JSON.stringify({ priority }),
      headers: { 'Content-Type': 'application/json' }
    }).then((response) => {
      if (response.ok) {
        enqueueSnackbar('Priority is set successfully', { variant: 'success' })
      } else {
        throw Error()
      }
    }).catch(() => {
      enqueueSnackbar('Failed to set priority', { variant: 'error' })
    }).then(() => {
      setBusy(false)
    })
  }, [enqueueSnackbar, job, cluster.id])
  const onBlur = useCallback((event: FocusEvent<HTMLInputElement>) => {
    if (input.current) {
      setPriority(input.current.valueAsNumber)
    }
  }, [setPriority])
  const onKeyDown = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    if (input.current === undefined) return
    if (event.key === 'Enter') {
      setPriority(input.current.valueAsNumber)
    }
    if (event.key === 'Escape') {
      input.current.value = priority
    }
  }, [setPriority, priority])

  if (editable) {
    return (
      <Input
        inputRef={input}
        type="number"
        defaultValue={priority}
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
    return <>{priority}</>
  }
}

const valueOf = (job: Job): number => {
  return job['priority'] != null ? job['priority'] : DEFAULT_PRIORITY
}

export default (): Column<Job> => ({
  title: 'Priority',
  type: 'numeric',
  render (job) {
    return <PriorityField job={job}/>
  },
  customSort (job1, job2) {
    return valueOf(job1) - valueOf(job2)
  }
})
