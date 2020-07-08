import { useEffect, useState } from 'react'
import useFetch from 'use-http'
import { useTimeoutFn } from 'react-use'

type Job = object
type UseJob = [Job | undefined, Error | undefined]

const useJob = (clusterId: string, jobId: string): UseJob => {
  const [job, setJob] = useState<Job>()
  const { data, error, get } = useFetch<Job>({
    url: `/api/clusters/${clusterId}/jobs/${jobId}`,
    onMount: true
  })
  const [isReady, reset, cancel] = useTimeoutFn(get, 15000)
  useEffect(() => {
    if (data === undefined) return

    setJob(data)

    if (isReady()) {
      reset()
    }
    return () => {
      cancel()
    }

  }, [data])

  if (job !== undefined) {
    return [job, undefined]
  }

  return [undefined, error]
}

export default useJob
