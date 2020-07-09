import { createContext } from 'react'

const Context = createContext({
  admin: false,
  data: {},
  getMeta () { }
})

export default Context
