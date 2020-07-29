import { createContext } from 'react'

export default createContext({
  cluster: undefined as any,
  accessible: false,
  admin: false,
  owned: false,
  job: undefined as any
})
