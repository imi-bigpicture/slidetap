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

import { FormControl, FormLabel } from '@mui/material'
import { alpha } from '@mui/material/styles'
import React from 'react'

interface OutlinedFormControlProps {
  label: string
  required?: boolean
  error?: boolean
  fullWidth?: boolean
  children: React.ReactElement
  rightLabel?: React.ReactElement
}

function OutlinedFormControl({
  label,
  required,
  error,
  fullWidth,
  children,
  rightLabel,
}: OutlinedFormControlProps): React.ReactElement {
  const childWithClassName = React.cloneElement(children, {
    className: `${children.props.className || ''} outlined-form-control-content`.trim(),
  })

  return (
    <FormControl
      required={required}
      error={error}
      size="small"
      variant="outlined"
      fullWidth={fullWidth}
      sx={{
        gap: 0.5,
        '& .outlined-form-control-content': {
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          padding: '2px 4px',
          borderRadius: (theme) => {
            const baseRadius = theme.shape.borderRadius
            return typeof baseRadius === 'number'
              ? baseRadius / 4
              : `calc(${baseRadius} / 4)`
          },
          border: (theme) =>
            `1px solid ${
              theme.palette.mode === 'light'
                ? alpha(theme.palette.common.black, 0.23)
                : alpha(theme.palette.common.white, 0.23)
            }`,
          backgroundColor: (theme) => theme.palette.background.paper,
          minHeight: 40,
          transition: (theme) =>
            theme.transitions.create(['border-color', 'box-shadow']),
        },
        '& .outlined-form-control-content:hover': {
          borderColor: (theme) =>
            theme.palette.mode === 'light'
              ? alpha(theme.palette.common.black, 0.87)
              : alpha(theme.palette.common.white, 0.87),
        },
        '& .outlined-form-control-content:focus-within': {
          borderColor: (theme) => theme.palette.primary.main,
          boxShadow: (theme) => `0 0 0 2px ${theme.palette.primary.main}40`,
        },
        '&.Mui-error .outlined-form-control-content': {
          borderColor: (theme) => theme.palette.error.main,
          boxShadow: 'none',
        },
      }}
    >
      <FormLabel
        sx={{
          position: 'absolute',
          top: 0,
          left: 12,
          px: 0.5,
          fontSize: '0.75rem',
          lineHeight: 1,
          color: 'text.secondary',
          backgroundColor: (theme) => theme.palette.background.paper,
          transform: 'translateY(-50%)',
          pointerEvents: 'none',
          zIndex: 1,
          '&.Mui-focused': {
            color: (theme) => theme.palette.primary.main,
          },
          '&.Mui-disabled': {
            color: (theme) => theme.palette.text.disabled,
          },
          '&.Mui-error': {
            color: (theme) => theme.palette.error.main,
          },
        }}
      >
        {label}
      </FormLabel>
      {rightLabel && (
        <FormLabel
          sx={{
            position: 'absolute',
            top: 0,
            right: 12,
            px: 0.5,
            fontSize: '0.75rem',
            lineHeight: 1,
            color: 'text.secondary',
            backgroundColor: (theme) => theme.palette.background.paper,
            transform: 'translateY(-50%)',
            pointerEvents: 'none',
            zIndex: 1,
            '&.Mui-focused': {
              color: (theme) => theme.palette.primary.main,
            },
            '&.Mui-disabled': {
              color: (theme) => theme.palette.text.disabled,
            },
            '&.Mui-error': {
              color: (theme) => theme.palette.error.main,
            },
          }}
        >
          {rightLabel}
        </FormLabel>
      )}
      {childWithClassName}
    </FormControl>
  )
}
export default OutlinedFormControl
