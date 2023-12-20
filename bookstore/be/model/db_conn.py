from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy import exists


class DBConn:
    def __init__(self):
        self.engine = store.get_db_conn()
        # self.cur = self.conn.cursor()
        self.client = store.get_mongo_conn()
        self.mongo = self.client["blob"]

    def user_id_exist(self, user_id):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        condition = exists().where(store.User.user_id == user_id)
        res = session.query(condition).scalar() != 0
        session.close()
        return res

    def book_id_exist(self, store_id, book_id):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        condition = exists().where(store.StoreStock.store_id == store_id, store.StoreStock.book_id == book_id)
        res = session.query(condition).scalar() != 0
        session.close()
        return res

    def store_id_exist(self, store_id):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        condition = exists().where(store.Store.store_id == store_id)
        res = session.query(condition).scalar() != 0
        session.close()
        return res
    
    def order_id_exist(self, order_id):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        condition = exists().where(store.Order.order_id == order_id)
        res = session.query(condition).scalar() != 0
        session.close()
        return res
