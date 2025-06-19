import { ReactElement } from 'react'
import { ItemDetailAction } from 'src/models/action'
import { Observation } from 'src/models/item'
import DisplayObservationAnnotation from '../reference/display_observation_annotation'
import DisplayObservationImage from '../reference/display_observation_image'
import DisplayObservationSample from '../reference/display_observation_sample'

interface ObservationLinkageProps {
  item: Observation
  action: ItemDetailAction
  handleItemOpen: (name: string, uid: string) => void

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

  const relation = [item.image, item.sample, item.annotation].find(
    (relation) => relation !== null,
  )
  if (relation === undefined) {
    return <></>
  }
  if (relation == item.sample) {
    return (
      <DisplayObservationSample
        action={action}
        schemaUid={item.schemaUid}
        references={[item.sample]}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleObservationItemsUpdate}
      />
    )
  }
  if (relation == item.image) {
    return (
      <DisplayObservationImage
        action={action}
        schemaUid={item.schemaUid}
        references={[item.image]}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleObservationItemsUpdate}
      />
    )
  }
  if (relation == item.annotation) {
    return (
      <DisplayObservationAnnotation
        action={action}
        schemaUid={item.schemaUid}
        references={[item.annotation]}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleObservationItemsUpdate}
      />
    )
  }
  throw new Error('Invalid observation relation')
}
