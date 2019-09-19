import React from "react";

export const handleChangeTab = (event: React.ChangeEvent<{}>, newValue: number,setValue: any,setShowIframe?: any) => {

  if (setShowIframe) {setShowIframe(false)}
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
