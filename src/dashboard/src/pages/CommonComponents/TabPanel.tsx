import React from "react";
import Typography from '@material-ui/core/Typography';
import Box from '@material-ui/core/Box';
interface TabPanelProps {
  children?: React.ReactNode;
  dir?: string;
  index: any;
  value: any;
}

export const TabPanel = (props: TabPanelProps) => {
      const { children, value, index, ...other } = props;
      return (
        <Typography
          component="div"
          role="tabpanel"
          hidden={value !== index}
          id={`full-width-tabpanel-${index}`}
          aria-labelledby={`full-width-tab-${index}`}
          {...other}
        >
          <Box p={3}>{children}</Box>
        </Typography>
      )
}
