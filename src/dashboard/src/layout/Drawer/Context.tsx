import React from "react";

const Context = React.createContext({
  open: false,
  setOpen(open: boolean) { this.open = open; }
});

export default Context;

export const Provider: React.FC = ({ children }) => {
  const [open, setOpen] = React.useState(false);
  return (
    <Context.Provider
      value={{ open, setOpen }}
      children={children}
    />
  );
};

export const WIDTH = 240;
