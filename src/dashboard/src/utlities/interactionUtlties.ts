import React from "react";

export const handleChangeTab = (event: React.ChangeEvent<{}>, newValue: number,setValue: any,setShowIframe?: any,setRefresh?: any) => {

  if (setShowIframe) {setShowIframe(false)}
  if (setRefresh) {setRefresh(false)
    setTimeout(()=>{
      setRefresh(true);
    },500);
  }

  setTimeout(()=>{
    if (setShowIframe) {
      setShowIframe(true);
    }
  },2000);
  setValue(newValue);
}

export const handleChangeIndex = (index: number, setValue: any) => {
  setValue(index);
}
