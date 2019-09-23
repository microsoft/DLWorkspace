import _ from "lodash";
import React from "react";

export const checkObjIsEmpty = (obj: object) => {
  return _.keys(obj).length === 0;
}

export const mergeTwoObjsByKey = (objs: any[], otherObjs: any[] ,key: string) => {
  const merged = _.merge(_.keyBy(objs, key), _.keyBy(otherObjs, key));
  return merged;
}

export const convertToArrayByKey = (objs: any, key: string) => {
  return _.map(objs,key);
}
export const filterByEventValue = (objs: any, key: string ,event: React.ChangeEvent<HTMLInputElement>) => {
  const  filtered= objs.filter((item: any)=>item[key] === event.target.value);
  return filtered
}




