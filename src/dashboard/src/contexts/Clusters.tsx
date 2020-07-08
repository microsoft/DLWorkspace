import * as React from 'react'
import {
  FunctionComponent,
  createContext,
  useContext,
  useMemo
} from "react"

import { find } from 'lodash'

import TeamContext from "./Team"
interface ClustersContext {
  clusters: any[];
}

const ClustersContext = createContext<ClustersContext>({ clusters: [] })

export default ClustersContext

export const Provider: FunctionComponent = ({ children }) => {
  const { teams, currentTeamId } = useContext(TeamContext)

  const clusters = useMemo(() => {
    const team = find(teams, ({ id }) => id === currentTeamId)
    if (team === undefined) return []
    return team['clusters']
  }, [teams, currentTeamId])

  return (
    <ClustersContext.Provider value={{ clusters }} children={children}/>
  )
}
