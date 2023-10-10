import {
  Button,
  DialogActions,
  DialogContent,
  MenuItem,
  Select,
  type SelectChangeEvent,
  Stack,
  TextField,
} from '@mui/material'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import React, { type ReactElement, useEffect, useState } from 'react'
import type { Mapper } from 'models/mapper'
import type { Attribute, Code } from 'models/attribute'
import mapperApi from 'services/api/mapper_api'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import WarningOutlinedIcon from '@mui/icons-material/WarningOutlined'
import Spinner from 'components/spinner'

export interface EditMappingProps {
  open: boolean
  attribute: Attribute<any, any>
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export function EditMapping({
  attribute,
  setOpen,
  open,
}: EditMappingProps): ReactElement {
  const [loading, setLoading] = useState(true)
  const [mappers, setMappers] = useState<Mapper[]>([])
  const [selectedMapper, setSelectedMapper] = useState<Mapper>()
  const handleDelete = (): void => {
    // mapperApi.delete(
    //     attribute.mapperId,
    //     attribute.mapping
    // ).catch(x => console.error('Failed to delete mapping', x))
    handleClose()
  }

  const handleSave = (): void => {
    // mapperApi.save(
    //     attribute.mapperId,
    //     attribute.mapping,
    //     attribute.mappedValue
    // ).catch(x => console.error('Failed to save mapping', x))
    handleClose()
  }

  const handleClose = (): void => {
    setOpen(false)
  }

  useEffect(() => {
    if (!open) {
      return
    }
    setLoading(true)
    // mapperApi.getForTag(attribute.tag)
    //     .then(
    //         mappers => {
    //             setMappers(mappers)
    //             const mapper = mappers?.filter(
    //                 mapper => mapper.uid === attribute.mapperUid
    //             )
    //             if (mapper.length === 1) {
    //                 setSelectedMapper(mapper[0])
    //             }
    //             setLoading(false)
    //         }
    //     ).catch(x => console.error('Failed to get mapper', x))
  }, [open, attribute])

  const handleMappedValueChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    // const { id, value } = event.target
    // if (isMappedStringAttribute(attribute)) {
    //     attribute.mappedValue = value
    // } else if (isMappedCodeAttribute(attribute)) {
    //     if (
    //         attribute.mappedValue === null ||
    //         attribute.mappedValue === undefined
    //     ) {
    //         attribute.mappedValue = { code: '', scheme: '', meaning: '' }
    //     }
    //     if (isCode(attribute.mappedValue)) {
    //         if (id === 'scheme') {
    //             attribute.mappedValue.scheme = value
    //         } else if (id === 'code') {
    //             attribute.mappedValue.code = value
    //         } else if (id === 'meaning') {
    //             attribute.mappedValue.meaning = value
    //         } else if (id === 'schemeVersion') {
    //             attribute.mappedValue.schemeVersion = value
    //         }
    //     }
    // }
  }

  const handleMapperIdChange = (event: SelectChangeEvent<number>): void => {
    // const { value } = event.target
    // if (typeof value === 'string') {
    //     attribute.mapperUid = value
    // }
  }

  const handleMappingChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    // attribute.mapping = value
  }
  return (
    <React.Fragment>
      {selectedMapper !== undefined && (
        <Dialog onClose={handleClose} open={open}>
          <DialogTitle>Edit mapping</DialogTitle>
          <DialogContent>
            <br />
            <Stack spacing={2}>
              <Spinner loading={loading}>
                {/* <DisplayMappableValue
                                    mappableValue={attribute.mappableValue}
                                />
                                <DisplayMappersSelection
                                    selectedMapper={selectedMapper}
                                    mappers={mappers}
                                    onChange={handleMapperIdChange} />
                                <DisplayMapping
                                    mapping={attribute.mapping}
                                    mappableValue={attribute.mappableValue}
                                    onChange={handleMappingChange} />
                                <DisplayMappedValue
                                    mapper={selectedMapper}
                                    mappedValue={attribute.mappedValue}
                                    onChange={handleMappedValueChange} /> */}
              </Spinner>
            </Stack>
          </DialogContent>
          <DialogActions style={{ justifyContent: 'space-between' }}>
            <Button onClick={handleSave}>Save</Button>
            <Button onClick={handleDelete}>Delete</Button>
            <Button onClick={handleClose}>Close</Button>
          </DialogActions>
        </Dialog>
      )}
    </React.Fragment>
  )
}

interface DisplayMappingProps {
  mapping?: string
  mappableValue?: string
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

function DisplayMapping({
  mapping,
  mappableValue,
  onChange,
}: DisplayMappingProps): ReactElement {
  let mappingFragment = <></>
  if (mapping !== undefined && mappableValue !== undefined) {
    if (new RegExp(mapping).test(mappableValue)) {
      mappingFragment = <CheckCircleIcon color="success" />
    } else {
      mappingFragment = <WarningOutlinedIcon color="warning" />
    }
  }

  return (
    <TextField
      label="mapping"
      defaultValue={mapping}
      onChange={onChange}
      InputProps={{ endAdornment: mappingFragment }}
    />
  )
}

interface DisplayMappableValueProps {
  mappableValue?: string
}

function DisplayMappableValue({
  mappableValue,
}: DisplayMappableValueProps): ReactElement {
  if (mappableValue === undefined) {
    return <></>
  }
  return <TextField disabled label="Mappable value" value={mappableValue} />
}

interface DisplayMappersSelectionProps {
  selectedMapper: Mapper
  mappers: Mapper[]
  onChange: (event: SelectChangeEvent<number>) => void
}

function DisplayMappersSelection({
  selectedMapper,
  mappers,
  onChange,
}: DisplayMappersSelectionProps): ReactElement {
  return (
    <Select label="Mapper id" onChange={onChange}>
      {mappers.map((mapper) => (
        <MenuItem key={mapper.uid} value={mapper.uid}>
          {mapper.name}
        </MenuItem>
      ))}
    </Select>
  )
}

interface DisplayMappedValueProps {
  mapper: Mapper
  mappedValue?: Attribute<any, any>
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

function DisplayMappedValue({
  mapper,
  mappedValue,
  onChange,
}: DisplayMappedValueProps): ReactElement {
  if (mappedValue === undefined) {
    return <></>
  }

  return <></>
}
