class SQLAlchemyError(Exception):
    pass


class IntegrityError(SQLAlchemyError):
    pass
