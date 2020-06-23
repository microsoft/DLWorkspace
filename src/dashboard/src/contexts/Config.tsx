import * as React from 'react';

interface Context {
  addGroup?: string;
  wiki?: string;
  support?: string;
  notifications?: { [team: string]: string };
}

const Context = React.createContext<Context>({});

export default Context;

export const Provider: React.FC<Context> = ({ children, ...props }) => {
  return <Context.Provider value={props} children={children}/>;
};
