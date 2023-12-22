import psycopg2
import uuid
import logging
from be.model import db_conn
from be.model import error
from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

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
            total_price = 0
            Session = sessionmaker(bind=self.engine)
            session = Session()

            for book_id, count in id_and_count:
                stock = session.query(store.StoreStock).filter_by(store_id=store_id, book_id=book_id).first()
                if not stock:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                if stock.stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                stock.stock_level -= count
                total_price += stock.price * count
                order_detail = store.OrderDetail(
                    order_id=uid,
                    book_id=book_id,
                    amount=count,
                    price=stock.price
                )
                session.add(order_detail)
            new_order = store.Order(
                order_id=uid,
                user_id=user_id,
                store_id=store_id,
                order_time=time_stamp,
                state="Pending",
                total_price=total_price
            )
            session.add(new_order)
            session.commit()
            session.close()
            order_id = uid
        except SQLAlchemyError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            Session = sessionmaker(bind=self.engine)
            session = Session()
            order = session.query(store.Order).filter_by(order_id=order_id).first()
            
            if not order:
                return error.error_invalid_order_id(order_id)

            if order.user_id != user_id:
                return error.error_authorization_fail()

            if order.state != "Pending":
                return error.error_illegal_order_state(order_id, order.state, "Pending")
            
            buyer_id = order.user_id
            assert buyer_id == user_id
            
            buyer = session.query(store.User).filter_by(user_id=user_id).first()
            if not buyer:
                return error.error_non_exist_user_id(user_id)

            if password != buyer.password:
                return error.error_authorization_fail()

            seller = session.query(store.User).join(store.Store).filter(store.Store.store_id == order.store_id).first()
            if not seller:
                return error.error_non_exist_store_id(order.store_id)

            if not self.user_id_exist(seller.user_id):
                return error.error_non_exist_user_id(seller.user_id)

            if buyer.balance < order.total_price:
                return error.error_not_sufficient_funds(order_id)

            buyer.balance -= order.total_price
            seller.balance += order.total_price
            order.state = 'ToShip'
            session.commit()
            session.close()

        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            Session = sessionmaker(bind=self.engine)
            session = Session()
            
            user_to_add = session.query(store.User).filter_by(user_id=user_id).first()
            if user_to_add:
                if user_to_add.password != password:
                    session.close()
                    return error.error_authorization_fail()
                user_to_add.balance += add_value
            else:
                session.close()
                return error.error_non_exist_user_id(user_id)

            session.commit()
            session.close()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"
    
    def funds(self, user_id, password) -> (int, str, int):
        try:
            Session = sessionmaker(bind=self.engine)
            session = Session()
            
            user = session.query(store.User).filter_by(user_id=user_id).first()
            if user:
                if user.password != password:
                    session.close()
                    return error.error_authorization_fail() + (0,)
                session.close()
                return 200, "ok", user.balance
            else:
                session.close()
                return error.error_non_exist_user_id(user_id) + (0,)
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e)) + (0,)
        except BaseException as e:
            return 530, "{}".format(str(e)) + (0,)
    
    
    # move specified order info to old_orders and set state to "Cancelled" or "Received"
    def archive_order(self, session, order_id, state) -> None:
        try:
            assert state in ["Cancelled", "Received"]
            
            order_to_archive = session.query(store.Order).filter_by(order_id=order_id).first()
            if order_to_archive:
                # init instance
                old_order = store.OldOrder(
                    order_id=order_to_archive.order_id,
                    user_id=order_to_archive.user_id,
                    store_id=order_to_archive.store_id,
                    order_time=order_to_archive.order_time,
                    state=state,
                    total_price=order_to_archive.total_price
                )

                # insert and delete
                session.add(old_order)
                session.delete(order_to_archive)

        except SQLAlchemyError as e:
            logging.info("528, {}".format(str(e)))
            return
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return
        return
    
    def confirm(self, user_id: str, password: str, order_id: str) -> (int, str):
        """
        1. Check userid, password, orderid
        2. Check order state, is it Shipped or not?
        3. Set order state to be Received.

        """
        try:          
            Session = sessionmaker(bind=self.engine)
            session = Session()
            # Check if the order exists
            order = session.query(store.Order).filter_by(order_id=order_id).first()
            if not order:
                return error.error_invalid_order_id(order_id)

            if order.user_id != user_id:
                return error.error_non_exist_user_id(user_id)

            if order.state != "Shipped":
                return error.error_illegal_order_state(order_id, order.state, "Shipped")

            # Check user info
            buyer = session.query(store.User).filter_by(user_id=user_id).first()
            if not buyer:
                return error.error_non_exist_user_id(user_id)

            if password != buyer.password:
                return error.error_authorization_fail()
            
            self.archive_order(session, order_id, "Received")
            session.commit()
            session.close()

        except SQLAlchemyError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"

    def cancel(self, user_id: str, password: str, order_id: str) -> (int, str):
        """
        1. Check userid, password, orderid
        2. Buyer can cancel order at any time until Received
        3. The balance of order will be refunded if order has been paid
        4. Set order state to be Canceled and archive it.

        """
        try:          
            Session = sessionmaker(bind=self.engine)
            session = Session()
            # Check if the order exists
            order = session.query(store.Order).filter_by(order_id=order_id).first()
            if not order:
                return error.error_invalid_order_id(order_id)
            order_id = order.order_id
            buyer_id = order.user_id
            store_id = order.store_id
            state = order.state
            total_price = order.total_price
            
            if buyer_id != user_id:
                return error.error_non_exist_user_id(user_id)
            
            if state == "Received":
                return error.error_illegal_order_state(order_id, state, "Not Received")
            if state == "Canceled":
                return error.error_illegal_order_state(order_id, state, "Not Cancelled")
            # Check pwd
            buyer = session.query(store.User).filter_by(user_id=user_id).first()
            if not buyer:
                return error.error_non_exist_user_id(user_id) 
            if buyer.password != password:
                return error.error_authorization_fail()
            
            if state != "Pending":
                # Refund balance
                seller = session.query(store.User).join(store.Store).filter(store.Store.store_id == store_id).first()
                if not seller:
                    return error.error_non_exist_store_id(order.store_id)

                buyer.balance += total_price
                seller.balance -= total_price
            
            self.archive_order(session, order_id, "Cancelled")
            session.commit()
            session.close()

        except SQLAlchemyError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        return 200, "ok"
    
    def list_orders(self, user_id: str, password: str, tle=30) -> (int, str, list):
        """
        list orders from collection `order` and `order archive`
        """
        try:
            result = []
            Session = sessionmaker(bind=self.engine)
            session = Session()
            
            user = session.query(store.User).filter_by(user_id=user_id).first()
            if not user:
                return *error.error_non_exist_user_id(user_id), []
            if password != user.password:
                return *error.error_authorization_fail(), []
            
            current_time = datetime.now()
            orders = session.query(store.Order).filter_by(user_id=user_id).all()
            # Check all orders in order collection where uid = user_id
            for order in orders:
                # Check for TLE
                order_id = order.order_id
                user_id = order.user_id
                store_id = order.store_id
                order_time = order.order_time
                state = order.state
                total_price = order.total_price
                if current_time - order_time > timedelta(seconds=tle):
                    self.archive_order(session, order_id, "Cancelled")  # Cancel the order if timeout
                    continue  # Do not add TLE orders to the result
                # print("###########ORDER INFO############: ", order)
                output = {
                    "oid": order_id,
                    "uid": user_id,
                    "sid": store_id,
                    "state": state,
                    "total_price": total_price,
                    "time": order_time,
                }
                result.append(output)  # Append non-TLE orders to result

            # Check all orders in order_archive collection where uid = user_id
            old_orders = session.query(store.OldOrder).filter_by(user_id=user_id).all()
            for order in old_orders:
                # print("###########ORDER INFO############: ", archived_order)
                order_id = order.order_id
                user_id = order.user_id
                store_id = order.store_id
                order_time = order.order_time
                state = order.state
                total_price = order.total_price
                output = {
                    "oid": order_id,
                    "uid": user_id,
                    "sid": store_id,
                    "state": state,
                    "total_price": total_price,
                    "time": order_time,
                }
                result.append(output)  # Append all archived orders to result            
            session.commit()
            session.close()
        except SQLAlchemyError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), []
        return 200, "ok", result