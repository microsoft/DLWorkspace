import React, {
  FunctionComponent,
  useContext
} from 'react';

import useFetch from 'use-http-2';

import Context from './Context';

const Console: FunctionComponent = () => {
  const { cluster, job } = useContext(Context);
  return <div>WIP</div>;
}

export default Console;
