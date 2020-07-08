import * as React from 'react'
import {AppBar, Container, Tabs, Tab} from "@material-ui/core"
import useCheckIsDesktop from "../../utlities/layoutUtlities"
import {handleChangeTab} from "../../utlities/interactionUtlties"
interface TabsProps {
  children?: React.ReactNode;
  value: any;
  setShowIframe?: any;
  setValue: any;
  titles: string[];
  setRefresh?: any;
}

export const DLTSTabs = (props: TabsProps) => {
  const { children, value,setShowIframe,setValue,titles,setRefresh, ...other } = props
  const checkIsDesktop = useCheckIsDesktop()
  return (
    <Container maxWidth={checkIsDesktop ? 'xl' : 'lg'}  >
      <AppBar position="static" color="default">
        <Tabs
          value={value}
          onChange={(event: React.ChangeEvent<{}>, value: number) => handleChangeTab(event,value,setValue,setShowIframe,setRefresh)}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
          {...other}
        >
          { titles && titles.map((title, index)=>(
            <Tab label={title} key={index}/>
          )) }
          {children}
        </Tabs>
      </AppBar>
    </Container>
  )
}
