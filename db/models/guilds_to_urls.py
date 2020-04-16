import sqlalchemy

from db.db_session import SqlAlchemyBase


class GuildsToUrls(SqlAlchemyBase):
    __tablename__ = 'guilds_to_urls'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    guild = sqlalchemy.Column(sqlalchemy.INTEGER, nullable=False)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    url = sqlalchemy.Column(sqlalchemy.String, nullable=False)
