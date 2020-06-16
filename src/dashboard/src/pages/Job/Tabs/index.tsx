import * as React from 'react';
import {
  FunctionComponent,
  ChangeEvent,
  useCallback,
  useMemo
} from 'react';
import {
  Paper,
  Tabs,
  Tab
} from '@material-ui/core';
import SwipeableViews from 'react-swipeable-views';

import useHashTab from '../../../hooks/useHashTab';

import Brief from './Brief';
import Endpoints from './Endpoints';
import Metrics from './Metrics';
import Console from './Console';

const JobTabs: FunctionComponent<{ manageable: boolean }> = ({ manageable }) => {
  const components = useMemo(() => manageable
    ? [Brief, Endpoints, Metrics, Console]
    : [Brief, Metrics, Console]
  , [manageable]);
  const [index, setIndex] = useHashTab(
    ...components.map(
      Component =>
        String(Component.displayName || Component.name).toLowerCase()));
  const onChange = useCallback((event: ChangeEvent<{}>, value: any) => {
    setIndex(value as number);
  }, [setIndex]);
  const onChangeIndex = useCallback((index: number, prevIndex: number) => {
    setIndex(index);
  }, [setIndex]);
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
            <Tab key={key} label={Component.displayName || Component.name}/>
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
  );
}

export default JobTabs;
