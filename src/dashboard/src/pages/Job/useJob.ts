import { useEffect, useState } from "react";
import useFetch from "use-http";

type Job = object;
type UseJob = [Job | undefined, Error | undefined];

const useJob = (clusterId: string, jobId: string): UseJob => {
  const [job, setJob] = useState<Job>();
  const { data, error, get } = useFetch<Job>({
    url: `/api/clusters/${clusterId}/jobs/${jobId}`,
    onMount: true
  });

  useEffect(() => {
    if (data === undefined) return;

    setJob(data);

    const timeout = setTimeout(get, 1000)
    return () => {
      clearTimeout(timeout);
    }
  }, [data]);

  if (job !== undefined) {
    return [job, undefined];
  }

  return [undefined, error];
}

export default useJob;
