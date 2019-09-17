import React, {useState} from "react";

import {
  Chip,
  Theme,
  createStyles,
  makeStyles } from "@material-ui/core";
import AddIcon from "@material-ui/icons/Add"
import RemoveIcon from "@material-ui/icons/Remove";
interface ServicesProps {
  services: string[];
}
const useStyles = makeStyles((theme: Theme) => {
  return createStyles({
    ChipsColor:{
      color:"secondary"
    }
  });
});
const ServicesChips: React.FC<ServicesProps> = ({services}) => {
  const styles = useStyles();
  const [showMoreDetails, setShowMoreDetails] = useState(false);
  const [details, setDetails] = useState('...');
  const handleShowMoreDetails = () => {
    setShowMoreDetails(!showMoreDetails);
    if (details === '...') {
      setDetails('');
    } else {
      setDetails('...');
    }
  }
  return (
    <>
      { services.map(( service,idx ) => {
        if (idx > 3) {
          return showMoreDetails ? (
            <Chip label={service} key={idx} />
          ):null
        } else if (idx === 3) {
          return ( <Chip  icon={showMoreDetails ? <RemoveIcon /> : <AddIcon /> } key={idx}label={`${service}${details}`} color="primary" onClick={handleShowMoreDetails}/>)
        }
        return (<Chip key={idx} label={service} />)
      }) }
  </>
  )
}

export default ServicesChips;
