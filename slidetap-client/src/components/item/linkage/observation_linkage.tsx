import { Card, CardContent, CircularProgress } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Action } from 'models/action'
import { Observation } from 'models/item'
import { ObservationSchema } from 'models/schema/item_schema'
import { ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'
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
  const schemaQuery = useQuery({
    queryKey: ['itemSchema', item.schemaUid],
    queryFn: async () => {
      return await schemaApi.getItemSchema<ObservationSchema>(item.schemaUid)
    },
  })
  const handleObservationItemsUpdate = (references: string[]): void => {
    const updatedItem = { ...item, item: references[0] }
    setItem(updatedItem)
  }
  if (schemaQuery.isLoading || schemaQuery.data === undefined) {
    return <CircularProgress />
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
            relations={schemaQuery.data.samples}
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
            relations={schemaQuery.data.images}
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
            relations={schemaQuery.data.annotations}
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
