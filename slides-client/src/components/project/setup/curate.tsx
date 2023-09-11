import React, { useEffect, useState, type ReactElement, Fragment } from 'react'
import type { Project } from 'models/project'

import projectApi from 'services/api/project_api'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Badge from '@mui/material/Badge'
import StepHeader from 'components/step_header'
import FormLabel from '@mui/material/FormLabel'
import FormGroup from '@mui/material/FormGroup'
import FormControlLabel from '@mui/material/FormControlLabel'
import Switch from '@mui/material/Switch'
import { AttributeTable } from 'components/table'
import type { ItemTableItem } from 'models/table_item'
import DisplayAttributeModal from 'components/item/display_attribute_modal'

interface CurateProps {
  project: Project
}

export default function Curate({ project }: CurateProps): ReactElement {
  const [showIncluded, setShowIncluded] = useState(true)
  const [showExcluded, setShowExcluded] = useState(true)
  const [loading, setLoading] = useState<boolean>(true)
  const [items, setItems] = useState<ItemTableItem[]>([])
  const [tabValue, setTabValue] = useState(0)
  const [attributeOpen, setAttributeOpen] = React.useState(false)
  const [attributeUid, setAttributeUid] = React.useState<string>()

  useEffect(() => {
    const getItems = (): void => {
      projectApi
        .getItems(
          project.uid,
          project.itemSchemas[tabValue].uid,
          showIncluded,
          showExcluded,
        )
        .then((items) => {
          setItems(items)
          setLoading(false)
        })
        .catch((x) => {console.error('Failed to get items', x)})
    }
    getItems()
    // const intervalId = setInterval(() => {
    //     getItems()
    // }, 10000)
    // return () => clearInterval(intervalId)
  }, [tabValue, project, showIncluded, showExcluded])

  const handleTabChange = (event: React.SyntheticEvent, newValue: number): void => {
    setLoading(true)
    setTabValue(newValue)
  }

  const handleAttributeOpen = (item: ItemTableItem, cellId: string): void => {
    if (cellId.startsWith('attributes.')) {
      const attributeName = cellId.split('attributes.').pop()
      if (attributeName === undefined) {
        return
      }
      const attributeUid = item.attributes[attributeName].uid
      setAttributeUid(attributeUid)
      setAttributeOpen(true)
    }
  }

  const handleIncludeChange = (itemUid: string, included: boolean): void => {
    projectApi
      .selectItem(project.uid, itemUid, included)
      .catch((x) => {console.error('Failed to set include for item', x)})
  }

  return (
    <Fragment>
      <StepHeader title="Curation" description="Curate items in project" />
      <FormGroup>
        <FormLabel>Show</FormLabel>
        <FormGroup row>
          <FormControlLabel
            control={<Switch value={showIncluded} checked={showIncluded} />}
            label="Included"
            onChange={(event, checked) => {setShowIncluded(checked)}}
          />
          <FormControlLabel
            control={<Switch value={showExcluded} checked={showExcluded} />}
            label="Excluded"
            onChange={(event, checked) => {setShowExcluded(checked)}}
          />
        </FormGroup>
      </FormGroup>
      <Tabs value={tabValue} onChange={handleTabChange}>
        {project.itemSchemas.map((item, index) => (
          <Tab
            key={index}
            label={
              <Badge badgeContent={project.itemCounts[index]} color="primary">
                {item.name}
              </Badge>
            }
          />
        ))}
      </Tabs>
      <AttributeTable
        columns={[
          { id: 'name', header: 'Name', accessorKey: 'name' },
          ...project.itemSchemas[tabValue].attributes.map((attribute) => {
            return {
              header: attribute.displayName,
              accessorKey: `attributes.${attribute.tag}.displayValue`,
              id: `attributes.${attribute.tag}`,
            }
          }),
        ]}
        data={items
          .filter((item) => {
            if (showIncluded && item.selected) {
              return true
            }
            if (showExcluded && !item.selected) {
              return true
            }
            return false
          })
          .map((item) => {
            return {
              uid: item.uid,
              name: item.name,
              selected: item.selected,
              attributes: item.attributes,
            }
          })}
        rowsSelectable={true}
        isLoading={loading}
        onCellClick={handleAttributeOpen}
        onRowSelect={handleIncludeChange}
      />
      {
        <DisplayAttributeModal
          attributeUid={attributeUid}
          open={attributeOpen}
          setOpen={setAttributeOpen}
        />
      }
    </Fragment>
  )
}
