import {
  createElement,
  forwardRef
} from 'react'

import MaterialTable, { Icons, MaterialTableProps } from 'material-table'
import {
  AddBox,
  ArrowDownward,
  Check,
  ChevronLeft,
  ChevronRight,
  Clear,
  DeleteOutline,
  Edit,
  FilterList,
  FirstPage,
  LastPage,
  Remove,
  SaveAlt,
  Search,
  SvgIconComponent,
  ViewColumn
} from '@material-ui/icons'

const forwardIcon = (Icon: SvgIconComponent) => forwardRef<SVGSVGElement>(function (props, ref) {
  return createElement(Icon, { fontSize: 'small', ref, ...props })
})

const icons: Icons = {
  Add: forwardIcon(AddBox),
  Check: forwardIcon(Check),
  Clear: forwardIcon(Clear),
  Delete: forwardIcon(DeleteOutline),
  DetailPanel: forwardIcon(ChevronRight),
  Edit: forwardIcon(Edit),
  Export: forwardIcon(SaveAlt),
  Filter: forwardIcon(FilterList),
  FirstPage: forwardIcon(FirstPage),
  SortArrow: forwardIcon(ArrowDownward),
  LastPage: forwardIcon(LastPage),
  NextPage: forwardIcon(ChevronRight),
  PreviousPage: forwardIcon(ChevronLeft),
  ResetSearch: forwardIcon(Clear),
  Search: forwardIcon(Search),
  ThirdStateCheck: forwardIcon(Remove),
  ViewColumn: forwardIcon(ViewColumn)
}

const SvgIconMaterialTable = function SvgIconMaterialTable<T extends object> (props: MaterialTableProps<T>) {
  return createElement<MaterialTableProps<T>>(MaterialTable, { icons, ...props })
}

export default SvgIconMaterialTable
