import { createContext } from 'react'

const Context = createContext({
  admin: false,
  data: {},
  getMeta () { return },
})

export default Context
