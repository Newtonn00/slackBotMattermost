from marshmallow import Schema, fields


class ConfigDTOSchema(Schema):
    slack_id = fields.Integer()
    last_datetime_synchronize = fields.Dict(fields.String)
    excluded_channels = fields.List(fields.String)
    excluded_users = fields.List(fields.String)

