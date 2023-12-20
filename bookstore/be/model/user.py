import jwt
import time
import logging

from be.model import error
from be.model import db_conn
from be.model import store
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded


# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            Session = sessionmaker(bind=self.engine)
            session = Session()
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            user = store.User(
                user_id=user_id, password=password, token=token, terminal=terminal, balance = 0
            )
            session.add(user)
            session.commit()
            session.close()
        except SQLAlchemyError as e:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_token(self, session, user_id: str, token: str) -> (int, str):
        row = session.query(store.User.token).filter_by(user_id=user_id).first()
        if row is None:
            return error.error_authorization_fail()
        db_token = row[0]
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        row = session.query(store.User.password).filter_by(user_id=user_id).first()
        if row is None:
            return error.error_authorization_fail()

        if password != row[0]:
            return error.error_authorization_fail()
        session.close()
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""
            Session = sessionmaker(bind=self.engine)
            session = Session()
            token = jwt_encode(user_id, terminal)
            user_to_update = session.query(store.User).filter_by(user_id=user_id).first()
            if user_to_update:
                user_to_update.token = token
                user_to_update.terminal = terminal
                session.commit()
                session.close()
            else:
                session.close()
                return error.error_authorization_fail() + ("",)
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            print(e)
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            Session = sessionmaker(bind=self.engine)
            session = Session()
            code, message = self.check_token(session, user_id, token)
            if code != 200:
                return code, message
            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)
            user_to_update = session.query(store.User).filter_by(user_id=user_id).first()
            if user_to_update:
                user_to_update.token = dummy_token
                user_to_update.terminal = terminal
                session.commit()
                session.close()
            else:
                session.close()
                return error.error_authorization_fail() + ("",)
            
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            print(e)
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message
            
            Session = sessionmaker(bind=self.engine)
            session = Session()
            user_to_unreg = session.query(store.User).filter_by(user_id=user_id).all()

            if len(user_to_unreg) == 1:
                session.delete(user_to_unreg[0])
                session.commit()
                session.close()
            else:
                # self.conn.rollback()
                session.close()
                return error.error_authorization_fail()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message
            Session = sessionmaker(bind=self.engine)
            session = Session()
            user_to_pwd = session.query(store.User).filter_by(user_id=user_id).all()
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            
            if len(user_to_pwd) == 1:
                user_to_pwd[0].password = new_password
                user_to_pwd[0].token = token
                user_to_pwd[0].terminal = terminal
                session.commit()
                session.close()

            else:
                session.close()
                return error.error_authorization_fail()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
