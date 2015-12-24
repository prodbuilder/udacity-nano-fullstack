from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
import datetime
import sqlalchemy

DB_NAME = 'postgresql://catalog:udacity@localhost/catalog'

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), unique=True, nullable=False)
    picture = Column(String(500), nullable=True)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'name'         : self.name,
           'email'        : self.email,
           'id'           : self.id,
           'picture'      : self.picture,
        }


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key = True)
    name = Column(String(100), nullable = False, unique = True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'name'         : self.name,
           'id'           : self.id,
        }


class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key = True)
    name = Column(String(100), nullable = False, unique = True)
    description = Column(String(500))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category, backref = backref('items', cascade = 'all, delete-orphan'))
    last_updated = Column(DateTime, server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now())
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    picture = Column(String(500))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
           'name'         : self.name,
           'id'           : self.id,
           'description'  : self.description,
           'last_updated' : self.last_updated,
           'category'     : self.category.name,
           'picture'      : self.picture,
        }


# engine = create_engine('sqlite:///catalog.db')
engine = create_engine(DB_NAME)

Base.metadata.create_all(engine)
