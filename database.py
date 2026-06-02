from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///gabinete_inteligente.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)
def init_db():
    Base.metadata.create_all(engine)
