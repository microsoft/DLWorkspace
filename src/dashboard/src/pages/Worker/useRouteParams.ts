import { useParams } from 'react-router';

interface RouteParams {
  clusterId: string;
  workerName: string;
}

const useRouteParams = () => {
  return useParams<RouteParams>();
}

export default useRouteParams;
