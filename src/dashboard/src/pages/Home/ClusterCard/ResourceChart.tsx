import * as React from 'react';
import {
  FunctionComponent,
  ComponentPropsWithoutRef,
  useCallback,
  useMemo,
  useState
} from 'react';

import {
  colors
} from '@material-ui/core'

import {
  Cell,
  Label,
  PieChart,
  Pie,
  PolarViewBox,
  ResponsiveContainer,
  Sector,
  Text
} from 'recharts';

import { capitalize, get, map, sumBy, transform } from 'lodash';

import { useCluster } from './Context';

const getActiveShape = ({ innerRadius, outerRadius, ...props }: ComponentPropsWithoutRef<typeof Sector>) => {
  return (
    <Sector
      innerRadius={Number(innerRadius) - 6}
      outerRadius={Number(outerRadius) + 6}
      {...props}
    />
  );
};

const getLabelContent = ({ viewBox, offset, ...props }: ComponentPropsWithoutRef<typeof Label>) => {
  const { cx, cy, innerRadius, outerRadius } = viewBox as PolarViewBox;
  const x = Number(cx) - Number(offset);
  const y = Number(cy) - (Number(innerRadius) + Number(outerRadius)) / 2;
  const width = x;
  const { fill, children } = props
  return (
    <Text
      textAnchor="end"
      verticalAnchor="middle"
      fontWeight="bold"
      {...{ x, y, width, fill, children }}
    />
  );
};

const pieProps: ComponentPropsWithoutRef<typeof Pie> = {
  nameKey: 'name',
  dataKey: 'value',
  startAngle: 90,
  endAngle: -180,
  activeShape: getActiveShape
};

const ResourceChart: FunctionComponent = () => {
  const { status } = useCluster();

  const [active, setActive] = useState<{
    pie: 'cpu' | 'gpu';
    index: number;
  }>();

  const { cpu, gpu } = useMemo(() => {
    const { cpu, gpu } = transform(status.types, (data, type) => {
      data.cpu.available += get(type, ['cpu', 'available'], 0);
      data.cpu.used += get(type, ['cpu', 'used'], 0);
      data.cpu.unschedulable += get(type, ['cpu', 'unschedulable'], 0);
      data.gpu.available += get(type, ['gpu', 'available'], 0);
      data.gpu.used += get(type, ['gpu', 'used'], 0);
      data.gpu.unschedulable += get(type, ['gpu', 'unschedulable'], 0);
    }, {
      cpu: { available: 0, used: 0, unschedulable: 0 },
      gpu: { available: 0, used: 0, unschedulable: 0 }
    });
    return {
      cpu: map(cpu, (value, name) => ({ name, value })),
      gpu: map(gpu, (value, name) => ({ name, value })),
    }
  }, [status]);
  const cpuTotal = useMemo(() => sumBy(cpu, 'value'), [cpu]);
  const gpuTotal = useMemo(() => sumBy(gpu, 'value'), [gpu]);

  const cpuLabelProps = useMemo(() => {
    if (cpu === undefined) return {};
    const totalCPUs = `${cpuTotal} CPU${cpuTotal === 1 ? '' : 's'}`;
    if (active === undefined || active.pie === 'gpu') {
      return { children: totalCPUs }
    }
    const { name, value } = cpu[active.index];
    const children = `${value} of ${totalCPUs} ${capitalize(name)}`;
    if (name === 'unschedulable') {
      return { fill: colors.red[500] , children };
    } else {
      return { children };
    }
  }, [active, cpu, cpuTotal]);
  const gpuLabelProps = useMemo(() => {
    if (gpu === undefined) return {};
    const totalGPUs = `${gpuTotal} GPU${gpuTotal === 1 ? '' : 's'}`;
    if (active === undefined || active.pie === 'cpu') {
      return { children: totalGPUs }
    }
    const { name, value } = gpu[active.index];
    const children = `${value} of ${totalGPUs} ${capitalize(name)}`;
    if (name === 'unschedulable') {
      return { fill: colors.red[500] , children };
    } else {
      return { children };
    }
  }, [active, gpu, gpuTotal]);

  const handleCPUMouseEnter = useCallback((data: unknown, index: number) => {
    setActive({ pie: 'cpu', index })
  }, [setActive]);
  const handleGPUMouseEnter = useCallback((data: unknown, index: number) => {
    setActive({ pie: 'gpu', index })
  }, [setActive]);

  return (
    <ResponsiveContainer aspect={1}>
      <PieChart>
        { cpu && cpuTotal && (
          <Pie
            data={cpu}
            innerRadius={64}
            outerRadius={88}
            activeIndex={active && active.pie === 'cpu' ? active.index : undefined}
            onMouseEnter={handleCPUMouseEnter}
            {...pieProps}
          >
            <Label content={getLabelContent} fill={colors.green[500]} {...cpuLabelProps}/>
            <Cell key='available' fill={colors.green[500]}/>
            <Cell key='used'  fill={colors.green[100]}/>
            <Cell key='unschedulable'  fill={colors.red[100]}/>
          </Pie>
        ) }
        { gpu && gpuTotal && (
          <Pie
            data={gpu}
            innerRadius={90}
            outerRadius={114}
            activeIndex={active && active.pie === 'gpu' ? active.index : undefined}
            onMouseEnter={handleGPUMouseEnter}
            {...pieProps}
          >
            <Label content={getLabelContent} fill={colors.lightBlue[500]} {...gpuLabelProps}/>
            <Cell key='available' fill={colors.lightBlue[500]}/>
            <Cell key='used'  fill={colors.lightBlue[100]}/>
            <Cell key='unschedulable'  fill={colors.red[100]}/>
          </Pie>
        ) }
      </PieChart>
    </ResponsiveContainer>
  )
}

export default ResourceChart;
