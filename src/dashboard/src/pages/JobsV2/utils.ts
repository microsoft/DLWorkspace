import { groupBy } from 'lodash';

export type Job = any;

const ACTIVE_STATUS = new Set([
  "unapproved",
  "queued",
  "scheduling",
  "running",
  "pausing",
  "paused",
])

export const groupByActive = (jobs: Array<Job>) => {
  return groupBy(jobs, (job) => {
    return ACTIVE_STATUS.has(job['jobStatus']);
  });
};
