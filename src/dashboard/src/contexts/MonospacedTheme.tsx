import React from "react";

import { createMuiTheme } from "@material-ui/core";
import { ThemeProvider } from "@material-ui/styles";

const theme = createMuiTheme({
  typography: {
    fontFamily: `"Roboto-mono", "Menlo", "Consolas", monospace`
  }
});

export default theme;

export const Provider: React.FC = ({ children }) => (
  <ThemeProvider theme={theme} children={children}/>
);
