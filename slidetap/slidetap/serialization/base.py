from marshmallow import Schema


class BaseModel(Schema):
    """Schema that uses camel-case for its external representation
    and snake-case for its internal representation.
    """

    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = self.camelcase(field_obj.data_key or field_name)

    @staticmethod
    def camelcase(name: str) -> str:
        parts = iter(name.split("_"))
        return next(parts) + "".join(i.title() for i in parts)
