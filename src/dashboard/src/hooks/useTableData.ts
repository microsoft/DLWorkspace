import { useReducer, useEffect } from 'react'
import { extend, get, set } from 'lodash'

const useTableData = <T extends object>(data: T[], defaults?: any) => {
  const [tableData, setTableData] = useReducer((currentData: T[], newData: T[]) => {
    if (newData == null) return newData
    if (currentData == null) currentData = []

    return newData.map((row, index) => {
      if (index < currentData.length) {
        set(row, 'tableData', get(currentData[index], 'tableData'))
      } else if (defaults) {
        set(row, 'tableData', extend(get(row, 'tableData'), defaults))
      }
      return row
    })
  }, data, (data) => {
    if (data == null || defaults == null) return data
    return data.map((row) => {
      set(row, 'tableData', defaults)
      return row
    })
  })

  useEffect(() => setTableData(data), [data])

  return tableData
}

export default useTableData
