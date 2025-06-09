from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class FrozenBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        frozen=True,
        from_attributes=True,
        populate_by_name=True,
    )
