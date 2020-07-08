import { createContext } from 'react'

interface ClusterContext {
  cluster?: any;
}

const ClusterContext = createContext<ClusterContext>({})

export default ClusterContext
