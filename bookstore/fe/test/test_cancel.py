import pytest
import uuid
from fe.access.new_buyer import register_new_buyer
from fe.test.gen_book_data import GenBook



class TestCancel:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.user_id = "test_cancel_{}".format(str(uuid.uuid1()))
        self.password = self.user_id
        self.buyer = register_new_buyer(self.user_id, self.password)
        # self.order_id = "test_cancel_order_id_{}".format(str(uuid.uuid1()))
        self.seller_id = "test_cancel_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_cancel_store_id_{}".format(str(uuid.uuid1()))
        self.gen_book = GenBook(self.seller_id, self.store_id)
        ok,buy_book_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        self.seller = self.gen_book.seller
        status_code,self.order_id = self.buyer.new_order(self.store_id,buy_book_list)
        assert status_code == 200
        code = self.buyer.add_funds(2147483647)
        assert code == 200

        code, funds = self.buyer.funds()
        assert code == 200
        self.funds = funds
        code = self.buyer.payment(self.order_id)
        assert code == 200

        yield

    def test_ok_and_err_state(self):
        code = self.buyer.cancel(self.order_id)
        assert code == 200
        # check state and fund
        code, funds = self.buyer.funds()
        assert code == 200
        assert funds == self.funds
        code, orders = self.buyer.list_orders()
        count = 0
        for order in orders:
            if order['oid'] == self.order_id:
                assert order['state'] == "Cancelled"
                count = 1
                break
        assert count != 0
        code = self.buyer.cancel(self.order_id)
        assert code == 520

    def test_error_user_id(self):
        self.buyer.user_id = self.buyer.user_id + "_x"
        code = self.buyer.cancel(self.order_id)
        assert code == 511

    def test_error_password(self):
        self.buyer.password = self.buyer.password + "_x"
        code = self.buyer.cancel(self.order_id)
        assert code == 401
        
    def test_error_order_id(self):
        self.order_id = self.order_id + "_x"
        code = self.buyer.cancel(self.order_id)
        assert code == 518