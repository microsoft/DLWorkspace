import React from "react";

interface Context {
  email?: string;
  uid?: string;
  familyName?: string;
  givenName?: string;
  token?: any;
}

const Context = React.createContext<Context>({});

export default Context;

interface ProviderProps {
  email?: string;
  uid?: string;
  familyName?: string;
  givenName?: string;
  token?: any;
}

export const Provider: React.FC<ProviderProps> = ({ email, uid,familyName, givenName,token,children }) => {
  if (token) {
    token = new Buffer(token.data).toString('hex');
  }
  return (
    <Context.Provider
      value={{ email,uid,familyName,givenName,token }}
      children={children}
    />
  );
};
