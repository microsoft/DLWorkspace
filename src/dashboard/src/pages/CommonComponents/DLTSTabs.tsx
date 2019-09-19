import React from "react";
import {AppBar, Container, Tabs, Tab} from "@material-ui/core";
import useCheckIsDesktop from "../../utlities/layoutUtlities";
import {handleChangeTab} from "../../utlities/interactionUtlties";
import { a11yProps } from "./a11yProps";
interface TabsProps {
  children?: React.ReactNode;
  value: any;
  setShowIframe?: any;
  setValue: any;
  titles: string[];
}

export const DLTSTabs = (props: TabsProps) => {
  const { children, value,setShowIframe,setValue,titles, ...other } = props;
  return (
    <Container maxWidth={useCheckIsDesktop ? 'lg' : 'xs'}  >
      <AppBar position="static" color="default">
        <Tabs
          value={value}
          onChange={(event: React.ChangeEvent<{}>, value: number) => handleChangeTab(event,value,setValue,setShowIframe)}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
          aria-label="full width tabs example"
          {...other}
        >
          { titles && titles.map((title, index)=>(
            <Tab label={title} {...a11yProps(index)} />
          )) }
          {children}
        </Tabs>
      </AppBar>
    </Container>
  )
}
