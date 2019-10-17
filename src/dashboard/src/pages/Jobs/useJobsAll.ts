import React, { useEffect, useState } from "react";
import useFetch from "use-http";
import TeamContext from "../../contexts/Teams";
import {useTimeoutFn} from "react-use";
type Jobs = object;
type useJobsAll = [Jobs | undefined, Error | undefined];

const useJobsAll = (openKillWarn?: boolean,openApproveWan?: boolean): useJobsAll => {
  const [jobsAll, setJobsAll] = useState<Jobs>();
  const { selectedTeam } = React.useContext(TeamContext);
  const params = new URLSearchParams({
    user:'all',
    limit:'100'
  });
  const { data, error, get } = useFetch<Jobs>('/api');
  const [isReady, reset, cancel] = useTimeoutFn(() => {
    get(`/teams/${selectedTeam}/jobs?${params}`);
  }, 3000);
  useEffect(() => {
    if (data == null) return;
    setJobsAll(data);

    if (isReady()) {
      reset();
    }
    return () => {
      cancel()
    }
  }, [data]);

  useEffect(() => {
    setJobsAll(undefined);
    get(`/teams/${selectedTeam}/jobs?${params}`);
  }, [selectedTeam]);


  if (jobsAll !== undefined) {
    return [jobsAll, undefined];
  }

  return [undefined, error];
}

export default useJobsAll;
