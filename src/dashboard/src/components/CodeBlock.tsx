import React, {
  FunctionComponent,
  useMemo
} from 'react';

import {
  Input,
  makeStyles,
  createStyles,
} from '@material-ui/core';

import { Provider as MonospacedThemeProvider } from '../contexts/MonospacedTheme';

const useStyles = makeStyles((theme) => createStyles({
  root: {
    color: 'inherit',
    fontSize: 'inherit',
  },
  input: {
    color: 'inherit',
    fontSize: 'inherit',
  }
}))

const CodeBlock: FunctionComponent<{ children: string }> = ({ children }) => {
  const styles = useStyles();
  const newLinedCode = useMemo(() => {
    if (children.charAt(children.length - 1) === '\n') {
      return children;
    }
    return children + '\n';
  }, [children])
  return (
    <MonospacedThemeProvider>
      <Input
        value={newLinedCode}
        fullWidth
        multiline
        readOnly
        disableUnderline
        margin="dense"
        classes={styles}
        inputProps={{
          style: {
            whiteSpace: 'pre',
            overflow: 'auto hidden',
          }
        }}
      />
    </MonospacedThemeProvider>
  );
};

export default CodeBlock;
