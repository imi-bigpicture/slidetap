import React, { ReactElement } from 'react'
import Button from '@mui/material/Button'
import projectApi from 'services/api/project_api'
import { Box } from '@mui/system'
import { Project } from 'models/project'
import StepHeader from 'components/step_header'

interface SubmitProps {
    project: Project
}

function Submit ({ project }: SubmitProps): ReactElement {
    const handleSubmitProject = (e: React.MouseEvent<HTMLElement>): void => {
        projectApi.submit(project.uid).catch(
            x => console.error('Failed to submit project', x)
        )
    }

    return (
        <React.Fragment>
            <StepHeader
                title='Submit'
                description='Submit exported images and metadata to destination.'
            />
            <Box sx={{ width: 300 }}>
                <Button onClick={handleSubmitProject}>Submit</Button>
            </Box>
        </React.Fragment>
    )
};

export default Submit
