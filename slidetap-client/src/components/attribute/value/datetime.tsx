//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import React from 'react'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { TimePicker } from '@mui/x-date-pickers/TimePicker'
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker'
import { ItemDetailAction } from 'src/models/action'
import { DatetimeType } from 'src/models/datetime_type'
import { DatetimeAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayDatetimeValueProps {
  value: Date | null
  schema: DatetimeAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: Date | null) => void
}

export default function DisplayDatetimeValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayDatetimeValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const dateValue = value !== null ? (value instanceof Date ? value : new Date(value)) : null
  const validDateValue = dateValue !== null && !isNaN(dateValue.getTime()) ? dateValue : null
  const valueValid = value !== null
  const nullIsOk = schema.optional && value === null

  const commonProps = {
    label: schema.displayName,
    value: validDateValue,
    onChange: (newValue: Date | null) => {
      handleValueUpdate(newValue)
    },
    readOnly: readOnly,
    slotProps: {
      textField: {
        size: 'small' as const,
        required: !schema.optional,
        error: !valueValid && !nullIsOk,
        fullWidth: true,
      },
    },
  }

  switch (schema.datetimeType) {
    case DatetimeType.DATE:
      return <DatePicker {...commonProps} />
    case DatetimeType.TIME:
      return <TimePicker {...commonProps} />
    case DatetimeType.DATETIME:
      return <DateTimePicker {...commonProps} />
  }
}
