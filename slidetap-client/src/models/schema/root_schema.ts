import { DatasetSchema } from "./dataset_schema"
import { AnnotationSchema, ImageSchema, ObservationSchema, SampleSchema } from "./item_schema"
import { ProjectSchema } from "./project_schema"

export interface RootSchema  {
    readonly uid: string,
    readonly name: string,
    readonly project: ProjectSchema,
    readonly dataset: DatasetSchema,
    readonly samples: Record<string, SampleSchema>,
    readonly images: Record<string, ImageSchema>,
    readonly observations: Record<string, ObservationSchema>,
    readonly annotations: Record<string, AnnotationSchema>,
}