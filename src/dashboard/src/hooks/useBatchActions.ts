import { createElement, useCallback, useMemo } from 'react'
import { useSnackbar } from 'notistack'
import { Action } from 'material-table'

import useConfirm from './useConfirm'
import { Check, Clear, Pause, PlayArrow } from '@material-ui/icons'

const APPROVABLE_STATUSES = [
  'unapproved'
]
const PAUSABLE_STATUSES = [
  'queued',
  'scheduling',
  'running'
]
const RESUMABLE_STATUSES = [
  'paused'
]
const KILLABLE_STATUSES = [
  'unapproved',
  'queued',
  'scheduling',
  'running',
  'pausing',
  'paused'
]

const useBatchActions = (clusterId: string) => {
  const confirm = useConfirm()
  const { enqueueSnackbar } = useSnackbar()

  const deselectAllJobs = (jobs: any[]) => {
    jobs.forEach(job => {
      if (job && job.tableData && job.tableData.checked === true) {
        job.tableData.checked = false
      }
    })
  }

  const batchUpdateStatus = useCallback((jobIds: string[], statusValue: string) => {
    const url = `/api/clusters/${clusterId}/jobs/status`
    const status = Object.create(null)
    for (const jobId of jobIds) {
      status[jobId] = statusValue
    }
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status })
    })
  }, [clusterId])

  const onBatchApprove = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} job(s)`
    return confirm(`Approve ${title}?`).then((answer) => {
      if (!answer) return

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being approved.`)
      return batchUpdateStatus(jobIds, 'approved').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s approve request is accepted.`, { variant: 'success' })
          deselectAllJobs(jobs)
        } else {
          enqueueSnackbar(`${title} are failed to approve.`, { variant: 'error' })
        }
      })
    })
  }, [confirm, enqueueSnackbar, batchUpdateStatus])

  const onBatchPause = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} job(s)`
    return confirm(`Pause ${title}?`).then((answer) => {
      if (!answer) return

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being paused.`)
      return batchUpdateStatus(jobIds, 'pausing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s pause request is accepted.`, { variant: 'success' })
          deselectAllJobs(jobs)
        } else {
          enqueueSnackbar(`${title} are failed to pause.`, { variant: 'error' })
        }
      })
    })
  }, [confirm, enqueueSnackbar, batchUpdateStatus])

  const onBatchResume = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} job(s)`
    return confirm(`Resume ${title}?`).then((answer) => {
      if (!answer) return

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being resumed.`)
      return batchUpdateStatus(jobIds, 'queued').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s resume request is accepted.`, { variant: 'success' })
          deselectAllJobs(jobs)
        } else {
          enqueueSnackbar(`${title} are failed to resume.`, { variant: 'error' })
        }
      })
    })
  }, [confirm, enqueueSnackbar, batchUpdateStatus])

  const onBatchKill = useCallback((event: any, jobs: any[]) => {
    const title = `${jobs.length} job(s)`
    return confirm(`Kill ${title}?`).then((answer) => {
      if (!answer) return

      const jobIds = jobs.map((job) => job['jobId'])

      enqueueSnackbar(`${title} are being killed.`)
      return batchUpdateStatus(jobIds, 'killing').then((response) => {
        if (response.ok) {
          enqueueSnackbar(`${title}'s kill request is accepted.`, { variant: 'success' })
          deselectAllJobs(jobs)
        } else {
          enqueueSnackbar(`${title} are failed to kill.`, { variant: 'error' })
        }
      })
    })
  }, [confirm, enqueueSnackbar, batchUpdateStatus])

  const batchApprove = useMemo(() => Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => APPROVABLE_STATUSES.indexOf(job['jobStatus']) === -1)
    return {
      hidden,
      icon: () => createElement(Check),
      tooltip: 'Approve',
      onClick: onBatchApprove
    }
  }, { position: 'toolbarOnSelect' }), [onBatchApprove])

  const batchPause = useMemo(() => Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => PAUSABLE_STATUSES.indexOf(job['jobStatus']) === -1)
    return {
      hidden,
      icon: () => createElement(Pause),
      tooltip: 'Pause',
      onClick: onBatchPause
    }
  }, { position: 'toolbarOnSelect' }), [onBatchPause])

  const batchResume = useMemo(() => Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => RESUMABLE_STATUSES.indexOf(job['jobStatus']) === -1)
    return {
      hidden,
      icon: () => createElement(PlayArrow),
      tooltip: 'Resume',
      onClick: onBatchResume
    }
  }, { position: 'toolbarOnSelect' }), [onBatchResume])

  const batchKill = useMemo(() => Object.assign((jobs: any[]): Action<any> => {
    const hidden = !Array.isArray(jobs) || jobs.some(job => KILLABLE_STATUSES.indexOf(job['jobStatus']) === -1)
    return {
      hidden,
      icon: () => createElement(Clear),
      tooltip: 'Kill',
      onClick: onBatchKill
    }
  }, { position: 'toolbarOnSelect' }), [onBatchKill])

  return { batchApprove, batchPause, batchResume, batchKill }
}

export default useBatchActions
