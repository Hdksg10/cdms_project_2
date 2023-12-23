import logging
import os
from pymongo import MongoClient
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, UniqueConstraint, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import threading

Base = declarative_base()
connect_url = "mongodb://userName:daseCDMS2023@110.40.142.252:27017"

class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    balance = Column(Integer, nullable=False)
    token = Column(String)
    terminal = Column(String)

class Store(Base):
    __tablename__ = 'stores'
    store_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    user = relationship('User')

class StoreStock(Base):
    __tablename__ = 'stores_stocks'
    store_id = Column(String, ForeignKey('stores.store_id'), primary_key=True)
    book_id = Column(String, primary_key=True)
    price = Column(Integer)
    stock_level = Column(Integer)
    __table_args__ = (UniqueConstraint('store_id', 'book_id'),)

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    store_id = Column(String, ForeignKey('stores.store_id'))
    order_time = Column(TIMESTAMP)
    state = Column(String)
    total_price = Column(Integer)
    user = relationship('User')
    store = relationship('Store')

class OrderDetail(Base):
    __tablename__ = 'orders_details'
    order_id = Column(String, ForeignKey('orders.order_id'), primary_key=True)
    book_id = Column(String, primary_key=True)
    amount = Column(Integer)
    price = Column(Integer)
    __table_args__ = (UniqueConstraint('order_id', 'book_id'),)

class OldOrder(Base):
    __tablename__ = 'old_orders'
    order_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    store_id = Column(String, ForeignKey('stores.store_id'))
    order_time = Column(TIMESTAMP)
    state = Column(String)
    total_price = Column(Integer)
    user = relationship('User')
    store = relationship('Store')

class OldOrderDetail(Base):
    __tablename__ = 'old_orders_details'
    order_id = Column(String, ForeignKey('old_orders.order_id'), primary_key=True)
    book_id = Column(String, primary_key=True)
    amount = Column(Integer)
    price = Column(Integer)
    __table_args__ = (UniqueConstraint('order_id', 'book_id'),)

def orm_init_tables(engine):
    Base.metadata.create_all(engine)


class StoreServer:
    database: str

    def __init__(self, host, port, user, pwd, db):
        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.db = db
        self.client = MongoClient(connect_url)
        self.engine = create_engine(f'postgresql://{user}:{pwd}@{host}:{port}/{db}')
        self.mongo = "blob"
        self.init_tables()

    def init_tables(self):
        
        orm_init_tables(self.engine)
        
        # init mongodb database
        collections = ["books"]
        indexs = {
            "books": [['store_id', 'book_id'], [('content', "text")]],
        }
        client = self.get_mongo_conn()
        db = client[self.mongo]     
        with client.start_session() as session:
            with session.start_transaction():
                try:
                    # create collections if not exist
                    collections_name = db.list_collection_names()
                    for collection in collections:
                        if collection not in collections_name:
                            db.create_collection(collection)
                            index = indexs.get(collection, None)
                            if index is not None:
                                for idx, ii in enumerate(index):
                                    isUnique = False
                                    if idx == 0: isUnique = True
                                    db[collection].create_index(ii, unique=isUnique)
                    session.commit_transaction()
                except Exception as e:
                    logging.error(e)
                    session.abort_transaction()
                 

    def get_db_conn(self):
        return self.engine
    
    def get_mongo_conn(self)-> MongoClient:
        return self.client
        


database_instance: StoreServer = None
init_completed_event = threading.Event()

def init_database(db_config):
    global database_instance
    database_instance = StoreServer(db_config["host"], db_config["port"], 
                              db_config["user"], db_config["pwd"],
                              db_config["db"],)
    print("database_instance: ", database_instance)

def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()

def get_mongo_conn():
    global database_instance
    return database_instance.get_mongo_conn()