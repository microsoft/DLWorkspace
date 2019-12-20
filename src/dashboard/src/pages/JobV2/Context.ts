import { createContext } from 'react';

interface Context {
  cluster: any;
  job: any;
}

export default createContext<Context>({
  cluster: undefined,
  job: undefined
});
