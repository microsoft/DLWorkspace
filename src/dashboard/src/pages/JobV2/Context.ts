import { createContext } from 'react';

interface Context {
  cluster: any;
  admin: boolean;
  job: any;
}

export default createContext<Context>({
  cluster: undefined,
  admin: false,
  job: undefined
});
