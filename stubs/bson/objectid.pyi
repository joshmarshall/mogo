import datetime


class ObjectId(object):

    @classmethod
    def from_datetime(cls, generation_time: datetime.datetime) -> "ObjectId": ...
