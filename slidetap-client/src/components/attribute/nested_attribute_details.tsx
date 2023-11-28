import React, { type ReactElement } from 'react'
import { Breadcrumbs, Link } from '@mui/material'
import type { Attribute } from 'models/attribute'
import DisplayAttribute from 'components/attribute/display_attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import HomeIcon from '@mui/icons-material/Home'

interface NestedAttributeDetailsProps {
  openedAttributes: Array<Attribute<any, any>>
  setOpenedAttributes: React.Dispatch<React.SetStateAction<Array<Attribute<any, any>>>>
  handleAttributeOpen: (attribute: Attribute<any, any>) => void
  handleAttributeUpdate?: (attribute: Attribute<any, any>) => void
}

export default function NestedAttributeDetails({
  openedAttributes,
  setOpenedAttributes,
  handleAttributeOpen,
  handleAttributeUpdate,
}: NestedAttributeDetailsProps): ReactElement {
  const handleBreadcrumbChange = (uid?: string): void => {
    if (uid === undefined) {
      setOpenedAttributes([])
      return
    }
    const parentAttributeIndex = openedAttributes.findIndex(
      (attribute) => attribute.uid === uid,
    )
    if (parentAttributeIndex >= 0) {
      setOpenedAttributes(openedAttributes.slice(0, parentAttributeIndex + 1))
    }
  }
  console.log('nested attribute details', handleAttributeUpdate)
  return (
    <Grid>
      <Breadcrumbs aria-label="breadcrumb">
        <Link
          onClick={() => {
            handleBreadcrumbChange()
          }}
        >
          <HomeIcon />
        </Link>
        {openedAttributes.map((attribute) => {
          return (
            <Link
              key={attribute.uid}
              onClick={() => {
                handleBreadcrumbChange(attribute.uid)
              }}
            >
              {attribute.schema.displayName}
            </Link>
          )
        })}
      </Breadcrumbs>
      <DisplayAttribute
        attribute={openedAttributes.slice(-1)[0]}
        hideLabel={false}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
      />
    </Grid>
  )
}
