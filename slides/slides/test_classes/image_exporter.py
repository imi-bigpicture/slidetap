from typing import Optional
from uuid import UUID

from apscheduler.job import Job

from slides.exporter.image import ImageExporter


class DummyImageExporter(ImageExporter):
    def _run_job(self, image_uid: UUID):
        pass

    def add_job(self, image_uid: UUID) -> Optional[Job]:
        pass
