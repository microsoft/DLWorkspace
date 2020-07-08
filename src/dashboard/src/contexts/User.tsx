import * as React from 'react'

interface Context {
  email?: string;
  familyName?: string;
  givenName?: string;
  password?: string;
}

const Context = React.createContext<Context>({})

export default Context

interface ProviderProps {
  email?: string;
  familyName?: string;
  givenName?: string;
  password?: string;
}

export const Provider: React.FC<ProviderProps> = ({ email, familyName, givenName, password, children }) => {
  return (
    <Context.Provider
      value={{ email, familyName, givenName, password }}
      children={children}
    />
  )
}
