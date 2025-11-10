from pydantic import BaseModel, ConfigDict


class FrozenBaseExternalModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )
