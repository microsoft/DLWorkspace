import { createContext } from 'react';

interface Context {
  cluster: any;
  accessible: boolean;
  admin: boolean;
  job: any;
}

export default createContext<Context>({
  cluster: undefined,
  accessible: false,
  admin: false,
  job: undefined
});
