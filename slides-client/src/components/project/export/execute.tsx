import React, { ReactElement, Fragment } from 'react'
import Button from '@mui/material/Button'
import projectApi from 'services/api/project_api'
import { Project } from 'models/project'
import { Box, Stack, TextField } from '@mui/material'
import StepHeader from 'components/step_header'

interface StartProps {
    project: Project
    nextView: string
    changeView: (to: string) => void
}

function Execute ({ project, nextView, changeView }: StartProps): ReactElement {
    const handleStartProject = (e: React.MouseEvent<HTMLElement>): void => {
        projectApi.start(project.uid).catch(
            x => console.error('Failed to start project', x)
        )
        changeView(nextView)
    }

    return (
        <Fragment>
            <StepHeader
                title='Execute'
                description='Execute export of project. This disables further changes in project.'
            />
            <Box sx={{ width: 300 }}>
                <Stack spacing={2}>
                    {project.itemSchemas.map(
                        (itemSchema, index) => <TextField
                            key={index}
                            label={itemSchema.name}
                            value={project.itemCounts[index]}
                            InputProps={{ readOnly: true }} />
                    )}
                    <Button onClick={handleStartProject}>Start</Button>
                </Stack>
            </Box>
        </Fragment>
    )
};

export default Execute
