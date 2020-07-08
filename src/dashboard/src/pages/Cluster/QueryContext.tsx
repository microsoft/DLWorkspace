import * as React from 'react'
import {
  FunctionComponent,
  createContext,
  useCallback,
  useEffect,
  useState
} from 'react'

interface Query {
  readonly current: string;
}

interface QueryContext {
  query?: string;
  setQuery(query: string): void;
}

const QueryContext = createContext<QueryContext>({
  setQuery () { return }
})

interface QueryProviderProps {
  onQueryChanged(query: string): void;
}

const QueryProvider: FunctionComponent<QueryProviderProps> = ({ onQueryChanged, children }) => {
  const [queryRef, setQueryRef] = useState<Query>()

  const query = queryRef && queryRef.current
  const setQuery = useCallback((query: string) => {
    setQueryRef({ current: query })
  }, [setQueryRef])

  useEffect(() => {
    if (queryRef !== undefined) {
      onQueryChanged(queryRef.current)
    }
  }, [queryRef, onQueryChanged])

  return <QueryContext.Provider value={{ query, setQuery }} children={children}/>
}

export default QueryContext
export { QueryProvider }
