import React, { ReactElement, Fragment } from 'react'
import { Typography } from '@mui/material'

interface StepHeaderProps {
    title: string
    description?: string
    instructions?: string
}

export default function StepHeader (
    { title, description, instructions }: StepHeaderProps
): ReactElement {
    return (
        <Fragment>
            <Typography variant='h4'>{title}</Typography>
            {description !== undefined &&
                <Typography variant='h6'>{description}</Typography>
            }
            {instructions !== undefined &&
                <Typography variant='subtitle1'>{instructions}</Typography>
            }
        </Fragment>
    )
}
