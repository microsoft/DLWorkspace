import * as React from 'react'
import {
  FunctionComponent,
  ComponentType,
  useCallback,
  useContext,
  useMemo
} from 'react'
import {
  Paper,
  Tabs,
  Tab
} from '@material-ui/core'
import SwipeableViews from 'react-swipeable-views'

import useHashTab from '../../../hooks/useHashTab'

import Context from '../Context'

import Brief from './Brief'
import Endpoints from './Endpoints'
import Metrics from './Metrics'
import Console from './Console'
import Apps from './Apps'

const getComponentName = (Component: ComponentType) => {
  if (Component.displayName !== undefined) {
    return Component.displayName
  }
  return Component.name
}

const JobTabs: FunctionComponent = () => {
  const { admin, owned } = useContext(Context)
  const components = useMemo(() => admin || owned
    ? [Brief, Endpoints, Metrics, Console, Apps]
    : [Brief, Metrics, Console]
  , [owned, admin])
  const [index, setIndex] = useHashTab(
    ...components.map(
      Component => getComponentName(Component).toLowerCase()))
  const onChange = useCallback((event: unknown, value: any) => {
    setIndex(value as number)
  }, [setIndex])
  const onChangeIndex = useCallback((index: number, prevIndex: number) => {
    setIndex(index)
  }, [setIndex])
  return (
    <Paper elevation={2}>
      <Tabs
        value={index}
        onChange={onChange}
        variant="fullWidth"
        textColor="primary"
        indicatorColor="primary"
      >
        {
          components.map((Component, key) => (
            <Tab key={key} label={getComponentName(Component)}/>
          ))
        }
      </Tabs>
      <SwipeableViews
        index={index}
        onChangeIndex={onChangeIndex}
      >
        {
          components.map((Component, key) =>
            index === key
              ? <Component key={key}/>
              : <div key={key}/>
          )
        }
      </SwipeableViews>
    </Paper>
  )
}

export default JobTabs
