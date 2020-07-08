import { createContext } from 'react'

interface DetailsContext {
  clusterId: string;
  jobId: string;
  cluster?: any;
  job: any;
}

export default createContext<DetailsContext>({
  clusterId: '',
  jobId: '',
  job: {}
})
