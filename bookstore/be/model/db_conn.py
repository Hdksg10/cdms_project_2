from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()
        self.cur = self.conn.cursor()
        self.client = store.get_mongo_conn()
        self.mongo = self.client["blob"]

    def user_id_exist(self, user_id):
        self.cur.execute(
            "SELECT user_id FROM users WHERE user_id = %s;", (user_id,)
        )
        return self.cur.rowcount != 0

    def book_id_exist(self, store_id, book_id):
        self.cur.execute(
            "SELECT book_id FROM stores_stocks WHERE store_id = %s AND book_id = %s;",
            (store_id, book_id),
        )
        return self.cur.rowcount != 0

    def store_id_exist(self, store_id):
        self.cur.execute(
            "SELECT store_id FROM stores WHERE store_id = %s;", (store_id,)
        )
        return self.cur.rowcount != 0
