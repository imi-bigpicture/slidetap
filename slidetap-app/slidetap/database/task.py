# import datetime
# from enum import Enum
# from typing import Optional
# from uuid import UUID, uuid4

# from sqlalchemy import Uuid
# from sqlalchemy.orm import Mapped

# from slidetap.database import db
# from slidetap.database.db import Base


# class TaskStatus(Enum):
#     PENDING = 1
#     RUNNING = 2
#     SUCCESS = 3
#     FAILURE = 4


# class DatabaseTask(Base):
#     uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
#     project_uid: Mapped[UUID] = db.Column(
#         Uuid, db.ForeignKey("project.uid"), index=True
#     )
#     batch_uid: Mapped[Optional[UUID]] = db.Column(
#         Uuid, db.ForeignKey("batch.uid"), index=True
#     )
#     status: Mapped[TaskStatus] = db.Column(
#         db.Enum(TaskStatus), default=TaskStatus.PENDING
#     )
#     message: Mapped[Optional[str]] = db.Column(db.String())
#     created: Mapped[datetime.datetime] = db.Column(db.DateTime)
#     started: Mapped[Optional[datetime.datetime]] = db.Column(db.DateTime)
#     completed: Mapped[Optional[datetime.datetime]] = db.Column(db.DateTime)
#     task: Mapped[Optional[str]] = db.Column(db.String())
