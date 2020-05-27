import {
  formatDistanceStrict,
  formatDistanceToNow
} from 'date-fns';

export function formatBytes(bytes: number) {
  if (bytes >= 1024 * 1024 * 1024 * 1024) {
    return (bytes / 1024 / 1024 / 1024 / 1024).toFixed(1) + ' TiB'
  }
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GiB'
  }
  if (bytes >= 1024 * 1024) {
    return (bytes / 1024 / 1024).toFixed(1) + ' MiB'
  }
  if (bytes >= 1024) {
    return (bytes / 1024).toFixed(1) + ' KiB'
  }
  if (isNaN(bytes)) {
    return '0 B'
  }
  return bytes + ' B'
}

export function formatFloat(float: number) {
  return String(Math.floor(float * 100) / 100);
}

export function formatPercent(float: number, digits = 2) {
  return String(Math.round(float * 100).toFixed(digits)) + '%'
}

export function formatHours(seconds: number) {
  return formatDistanceStrict(seconds * 1000, 0, {
    roundingMethod: 'round',
    unit: 'hour'
  })
}

export function formatDateDistance(date: Date) {
  return formatDistanceToNow(date, {
    includeSeconds: true,
    addSuffix: true
  })
}
