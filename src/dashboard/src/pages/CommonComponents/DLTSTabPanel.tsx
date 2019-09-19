import React from "react";
import Typography from '@material-ui/core/Typography';
import {Container, Paper, Toolbar} from "@material-ui/core";
import useCheckIsDesktop from "../../utlities/layoutUtlities";

interface TabPanelProps {
  children?: React.ReactNode;
  dir?: string;
  index: any;
  value: any;
  title?: string;
}

export const DLTSTabPanel = (props: TabPanelProps) => {
  const { children, value, index, title,...other } = props;
  return (
    <Container maxWidth={useCheckIsDesktop ? 'lg' : 'xs'}>
      <Typography
        component="div"
        role="tabpanel"
        hidden={value !== index}
        id={`full-width-tabpanel-${index}`}
        aria-labelledby={`full-width-tab-${index}`}
        {...other}
      >
        <Container maxWidth={useCheckIsDesktop ? 'lg' : 'xs'}>
          <Paper  style={{ display: useCheckIsDesktop ? 'block' : 'inline-block', marginTop: '10px', }}>
            <Toolbar>
              <Typography component="h2" variant="h6">
                {title}
              </Typography>
            </Toolbar>
            <Container maxWidth={'lg'}>
              {children}
            </Container>
          </Paper>
        </Container>

      </Typography>
    </Container>
  )
}
