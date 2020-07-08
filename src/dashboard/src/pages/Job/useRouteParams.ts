import { useParams } from 'react-router-dom'

interface RouteParams {
  clusterId: string
  jobId: string
}

const useRouteParams = () => useParams<RouteParams>()

export default useRouteParams
