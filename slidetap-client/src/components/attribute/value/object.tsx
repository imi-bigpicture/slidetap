import React from 'react'
import { FormControl, FormLabel } from '@mui/material'
import type { ObjectAttribute } from 'models/attribute'
import DisplayAttribute from '../display_attribute'
import Accordion from '@mui/material/Accordion'
import AccordionSummary from '@mui/material/AccordionSummary'
import AccordionDetails from '@mui/material/AccordionDetails'
import Typography from '@mui/material/Typography'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayObjectAttribute({
  attribute,
  hideLabel,
}: DisplayObjectAttributeProps): React.ReactElement {
  // if (attribute.value === undefined || attribute.value === null) {
  //     return <React.Fragment />
  // }
  return (
    <React.Fragment>
      <FormControl component="fieldset" variant="standard">
        {hideLabel !== true && (
          <FormLabel component="legend">{attribute.schema.displayName}</FormLabel>
        )}
        {attribute.value !== undefined && Object.values(attribute.value)
          // .filter(childAttribute => childAttribute.value !== null)
          // .filter(childAttribute => Object.keys(childAttribute.value).length !== 0)
          .map((childAttribute) => (
            <Accordion key={childAttribute.uid}>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="panel-content"
              >
                <Typography>{childAttribute.schema.displayName}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <DisplayAttribute
                  key={childAttribute.uid}
                  attribute={childAttribute}
                  hideLabel={true}
                />
              </AccordionDetails>
            </Accordion>
          ))}
      </FormControl>
    </React.Fragment>
  )
}
