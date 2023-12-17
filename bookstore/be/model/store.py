import logging
import os
from pymongo import MongoClient
import psycopg2

connect_url = "mongodb://userName:daseCDMS2023@110.40.142.252:27017"

class Store:
    database: str

    def __init__(self, host, port, user, pwd, db):
        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.db = db
        self.client = MongoClient(connect_url)
        self.mongo = "blob"
        self.init_tables()

    def init_tables(self):
        try:
            conn = self.get_db_conn()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, password TEXT NOT NULL, balance INTEGER NOT NULL, token TEXT, terminal TEXT);
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stores(store_id TEXT PRIMARY KEY,user_id TEXT,FOREIGN KEY (user_id) REFERENCES users(user_id));
                """
            )
            
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stores_stocks(
                    store_id TEXT,
                    book_id TEXT,
                    price INTEGER,
                    stock_level INTEGER,
                    FOREIGN KEY (store_id) REFERENCES stores(store_id),
                    CONSTRAINT store_stock UNIQUE (store_id, book_id)
                );
                """
            )
            
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders(
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    store_id TEXT,
                    order_time TIMESTAMP,
                    state TEXT,
                    total_price INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (store_id) REFERENCES stores(store_id)
                );
                """
            )
            
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders_details(
                    order_id TEXT,
                    book_id TEXT,
                    amount INTEGER,
                    price INTEGER,
                    CONSTRAINT order_detail UNIQUE (order_id, book_id)  
                );
                """
            )
            
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS old_orders(
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    store_id TEXT,
                    order_time TIMESTAMP,
                    state TEXT,
                    total_price INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (store_id) REFERENCES stores(store_id)
                );
                """
            )
            conn.commit()

        except psycopg2.Error as e:
            logging.error(e)
            conn.rollback()
        
        # init mongodb database
        collections = ["books"]
        indexs = {
            "books": [['store_id', 'book_id']],
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
        conn = psycopg2.connect(host = self.host, port = self.port,
                                user = self.user, password = self.pwd,
                                database = self.db)
        conn.set_session(autocommit=False)
        return conn
    
    def get_mongo_conn(self)-> MongoClient:
        return self.client
        


database_instance: Store = None


def init_database(db_config):
    global database_instance
    database_instance = Store(db_config["host"], db_config["port"], 
                              db_config["user"], db_config["pwd"],
                              db_config["db"],)
    print("database_instance: ", database_instance)

def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()

def get_mongo_conn():
    global database_instance
    return database_instance.get_mongo_conn()