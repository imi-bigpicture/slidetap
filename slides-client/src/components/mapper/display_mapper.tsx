import React, { useEffect, useState, ReactElement } from 'react'
import mapperApi from 'services/api/mapper_api'
import { Mapper } from 'models/mapper'
import { Route, useNavigate } from 'react-router-dom'
import EditMapper from 'components/mapper/edit_mapping_modal'
import Unmapped from 'components/mapper/unmapped_mapper'
import SideBar, { MenuSection } from 'components/side_bar'
import DisplayMappings from './display_mappings'
import MapperOverview from 'components/mapper/mapper_overview'
import DisplayMappingAttributes from './display_mapping_attributes'

const overviewSection = {
    name: 'Overview',
    path: ''
}

const mappingsSection = {
    name: 'Mappings',
    path: 'mappings'
}

const attributesSection = {
    name: 'Attributes',
    path: 'attributes'
}

const testSection: MenuSection = {
    name: 'Test',
    path: 'test'
}

const editSection: MenuSection = {
    name: 'Edit',
    path: 'edit'
}

const unmappedSection: MenuSection = {
    name: 'Unmapped',
    path: 'unmapped'
}

export default function DisplayMapper (): ReactElement {
    const [mapper, setMapper] = useState<Mapper | null>(null)
    const [view, setView] = useState<string>('')
    const navigate = useNavigate()

    function changeView (view: string): void {
        setView(view)
        navigate(view)
    }
    const mappertUid = window.location.pathname.split('mapping/').pop()?.split('/')[0]

    useEffect(() => {
        if (mappertUid === undefined) {
            return
        }
        mapperApi.get(mappertUid)
            .then(mapper => setMapper(mapper))
            .catch(x => console.error('Failed to get mapper', x))
    }, [mappertUid])

    if (mapper === null) {
        return (<></>)
    }

    const sections = [
        overviewSection,
        mappingsSection,
        attributesSection,
        testSection,
        editSection,
        unmappedSection
    ]

    const routes = [
        (<Route key="overview" path="/" element={<MapperOverview mapper={mapper} />} />),
        (<Route key="mappings" path="/mappings" element={<DisplayMappings mapper={mapper} />} />),
        (<Route key="attributes" path="/attributes" element={<DisplayMappingAttributes mapper={mapper} />} />),
        // (<Route key="test" path="/test" element={<TestMapper mapper={mapper} />} />),
        (<Route key="unmapped" path="/unmapped" element={<Unmapped mapper={mapper} />} />)
    ]
    return (
        <SideBar
            sections={sections}
            routes={routes}
            selectedView={view}
            changeView={changeView}
        />
    )
}
