
from be.model import error
from be.model import db_conn
import psycopg2
import json

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
            price = book_json.get('price', -1)
            self.cur.execute(
                "INSERT into stores_stocks(store_id, book_id, price, stock_level)"
                "VALUES (%s, %s, %s, %s)",
                (store_id, book_id, price, stock_level),
            )
            self.conn.commit()
            
            # insert blob data into mongodb
            book_collection = self.mongo["books"]
            book_json["store_id"] = store_id
            book_json["book_id"] = book_id
            book_collection.insert_one(book_json)
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
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

            self.cur.execute(
                "UPDATE stores_stocks SET stock_level = stock_level + %s "
                "WHERE store_id = %s AND book_id = %s",
                (add_stock_level, store_id, book_id),
            )
            self.conn.commit()
        except psycopg2.Error as e:
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
            self.cur.execute(
                "INSERT into stores(store_id, user_id)" "VALUES (%s, %s)",
                (store_id, user_id),
            )
            self.conn.commit()
        except psycopg2.Error as e:
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
            if not self.order_id_exist(order_id):
                # print(f"eo: {order_id}")
                return error.error_invalid_order_id(order_id)

            self.cur.execute(
                "SELECT state FROM orders WHERE order_id = %s",
                (order_id,),
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)
            state = row[0]
            if state != "ToShip":
                return error.error_illegal_order_state(order_id, state, "ToShip")
            
            self.cur.execute(
                "UPDATE orders SET state = 'Shipped' "
                "WHERE order_id = %s",
                (order_id,),
            )
  
            if self.cur.rowcount > 0:
                self.conn.commit()
                return 200 , "ok"
            else:
                raise psycopg2.Error()

        except psycopg2.Error as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))