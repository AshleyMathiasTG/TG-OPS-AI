"""SQLAlchemy declarative base and metadata."""
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        import re
        name = cls.__name__
        # CamelCase → snake_case
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
