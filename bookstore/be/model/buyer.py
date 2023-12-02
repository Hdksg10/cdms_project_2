import psycopg2
import uuid
import logging
from be.model import db_conn
from be.model import error
import time
from datetime import datetime

class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
        self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            time_stamp = datetime.now()
            
            self.cur.execute(
                "INSERT INTO orders(order_id, user_id, store_id, order_time, state) "
                "VALUES(%s, %s, %s, %s, %s);",
                (uid, user_id, store_id, time_stamp, "Pending"),
            )
            # self.conn.commit()
            for book_id, count in id_and_count:
                self.cur.execute(
                    "SELECT book_id, stock_level, price FROM stores_stocks "
                    "WHERE store_id = %s AND book_id = %s;",
                    (store_id, book_id),
                )
                row = self.cur.fetchone()
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row[1]
                price = row[2]

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.cur.execute(
                    "UPDATE stores_stocks set stock_level = stock_level - %s "
                    "WHERE store_id = %s and book_id = %s and stock_level >= %s; ",
                    (count, store_id, book_id, count),
                )
                if self.cur.rowcount == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.cur.execute(
                    "INSERT INTO orders_details(order_id, book_id, amount, price) "
                    "VALUES(%s, %s, %s, %s);",
                    (uid, book_id, count, price),
                )

            self.conn.commit()
            order_id = uid
        except psycopg2.Error as e:
            print(str(e))
            self.conn.rollback()
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            self.cur.execute(
                "SELECT order_id, user_id, store_id FROM orders WHERE order_id = %s",
                (order_id,),
            )
            self.cur.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row[0]
            buyer_id = row[1]
            store_id = row[2]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            self.cur.execute(
                "SELECT balance, password FROM users WHERE user_id = %s;", (buyer_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = row[0]
            if password != row[1]:
                return error.error_authorization_fail()

            self.cur.execute(
                "SELECT store_id, user_id FROM stores WHERE store_id = %s;",
                (store_id,),
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = row[1]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            self.cur.execute(
                "SELECT book_id, amount, price FROM orders_details WHERE order_id = %s;",
                (order_id,),
            )
            rows = self.cur.fetchall()
            total_price = 0
            for row in rows:
                count = row[1]
                price = row[2]
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            self.cur.execute(
                "UPDATE users set balance = balance - %s"
                "WHERE user_id = %s AND balance >= %s",
                (total_price, buyer_id, total_price),
            )
            if self.cur.rowcount == 0:
                return error.error_not_sufficient_funds(order_id)

            self.cur.execute(
                "UPDATE users set balance = balance + %s" "WHERE user_id = %s",
                (total_price, buyer_id),
            )

            if self.cur.rowcount == 0:
                return error.error_non_exist_user_id(buyer_id)

            self.cur.execute(
                "UPDATE orders set state = \"ToShip\""
                "WHERE order_id = %s",
                (order_id,)
            )
            assert self.cur.rowcount == 1
            # self.cur.execute(
            #     "DELETE FROM orders WHERE order_id = %s", (order_id,)
            # )
            # if self.cur.rowcount == 0:
            #     return error.error_invalid_order_id(order_id)

            # self.cur.execute(
            #     "DELETE FROM orders_details where order_id = %s", (order_id,)
            # )
            # if self.cur.rowcount == 0:
            #     return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            self.cur.execute(
                "SELECT password from users where user_id=%s", (user_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_authorization_fail()

            if row[0] != password:
                return error.error_authorization_fail()

            self.cur.execute(
                "UPDATE users SET balance = balance + %s WHERE user_id = %s",
                (add_value, user_id),
            )
            if self.cur.rowcount == 0:
                return error.error_non_exist_user_id(user_id)

            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"
