import { AnnotationSchema, ImageSchema, ObservationSchema, SampleSchema } from "./item_schema"
import { ProjectSchema } from "./project_schema"

export type RootSchema = {
    uid: string,
    name: string,
    project: ProjectSchema,
    samples: Record<string, SampleSchema>,
    images: Record<string, ImageSchema>,
    observations: Record<string, ObservationSchema>,
    annotations: Record<string, AnnotationSchema>,
}