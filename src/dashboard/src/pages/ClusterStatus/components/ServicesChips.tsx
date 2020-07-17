import * as React from 'react'
import { useState } from 'react'

import {
  Chip
} from '@material-ui/core'
import AddIcon from '@material-ui/icons/Add'
import RemoveIcon from '@material-ui/icons/Remove'
interface ServicesProps {
  services: string[]
}

const ServicesChips: React.FC<ServicesProps> = ({ services }) => {
  const [showMoreDetails, setShowMoreDetails] = useState(false)
  const [details, setDetails] = useState('...')
  const handleShowMoreDetails = () => {
    setShowMoreDetails(!showMoreDetails)
    if (details === '...') {
      setDetails('')
    } else {
      setDetails('...')
    }
  }
  return (
    <>
      { services.map((service, idx) => {
        if (idx > 3) {
          return showMoreDetails ? (
            <Chip label={service} key={idx} />
          ) : null
        } else if (idx === 3) {
          return (<Chip icon={showMoreDetails ? <RemoveIcon /> : <AddIcon /> } key={idx}label={`${service}${details}`} color="primary" onClick={handleShowMoreDetails}/>)
        }
        return (<Chip key={idx} label={service} />)
      }) }
    </>
  )
}

export default ServicesChips
