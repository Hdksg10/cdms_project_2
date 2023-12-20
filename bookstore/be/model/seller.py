
from be.model import error
from be.model import db_conn
from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json
import jieba

class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)
            book_json = json.loads(book_json_str)
            content = book_json.get('content', " ")
            content_words = jieba.lcut_for_search(content)
            content_segmented = " ".join(content_words)
            price = book_json.get('price', -1)
            # self.cur.execute(
            #     "INSERT into stores_stocks(store_id, book_id, price, stock_level)"
            #     "VALUES (%s, %s, %s, %s)",
            #     (store_id, book_id, price, stock_level),
            # )
            # self.conn.commit()
            Session = sessionmaker(bind=self.engine)
            session = Session()
            book = store.StoreStock(
                store_id = store_id, book_id = book_id, price = price, stock_level = stock_level
            )
            session.add(book)
            session.commit()
            session.close()
            # insert blob data into mongodb
            book_collection = self.mongo["books"]
            book_json["store_id"] = store_id
            book_json["book_id"] = book_id
            book_json["content_seg"] = content_segmented
            book_collection.insert_one(book_json)
        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)
            Session = sessionmaker(bind=self.engine)
            session = Session()
            stock_to_update = session.query(store.StoreStock).filter_by(store_id=store_id, book_id=book_id).first()
            stock_to_update.stock_level += add_stock_level
            session.commit()
            session.close()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            Session = sessionmaker(bind=self.engine)
            session = Session()
            book = store.Store(
                store_id = store_id, user_id = user_id
            )
            session.add(book)
            session.commit()
            session.close()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def handle_order(self, user_id: str, store_id : str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            Session = sessionmaker(bind=self.engine)
            session = Session()
            order = session.query(store.Order).filter_by(order_id=order_id).first()
            if not order:
                return error.error_invalid_order_id(order_id)
            if order.state != "ToShip":
                return error.error_illegal_order_state(order_id, order.state, "ToShip")

            order.state = "Shipped"
            session.commit()
            session.close()
            return 200, "ok"

        except SQLAlchemyError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))