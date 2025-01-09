import { Card, CardContent } from '@mui/material'
import { Action } from 'models/action'
import { Observation } from 'models/item'
import { ReactElement } from 'react'
import DisplayObservationAnnotation from '../reference/display_observation_annotation'
import DisplayObservationImage from '../reference/display_observation_image'
import DisplayObservationSample from '../reference/display_observation_sample'

interface ObservationLinkageProps {
  item: Observation
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: Observation) => void
}

export default function ObservationLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ObservationLinkageProps): ReactElement {
  const handleObservationItemsUpdate = (references: string[]): void => {
    const updatedItem = { ...item, item: references[0] }
    setItem(updatedItem)
  }

  const relation = [item.image, item.sample, item.annotation].find((relation) => {
    relation !== undefined
  })
  if (relation === undefined) {
    return <></>
  }
  if (relation == item.sample) {
    return (
      <Card>
        <CardContent>
          <DisplayObservationSample
            action={action}
            schemaUid={item.schemaUid}
            references={[item.item]}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleObservationItemsUpdate}
          />
        </CardContent>
      </Card>
    )
  }
  if (relation == item.image) {
    return (
      <Card>
        <CardContent>
          <DisplayObservationImage
            action={action}
            schemaUid={item.schemaUid}
            references={[item.item]}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleObservationItemsUpdate}
          />
        </CardContent>
      </Card>
    )
  }
  if (relation == item.annotation) {
    return (
      <Card>
        <CardContent>
          <DisplayObservationAnnotation
            action={action}
            schemaUid={item.schemaUid}
            references={[item.item]}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleObservationItemsUpdate}
          />
        </CardContent>
      </Card>
    )
  }
  throw new Error('Invalid observation relation')
}
