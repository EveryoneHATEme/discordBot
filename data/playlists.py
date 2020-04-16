import datetime
import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Playlist(SqlAlchemyBase):
    __tablename__ = 'playlists'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    url = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    user = orm.relation('User')

    def __repr__(self):
        return f'news id:{self.id} title: {self.title}  is_private: {self.is_private}  user_id: {self.user_id}'