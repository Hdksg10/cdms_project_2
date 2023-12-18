import pytest
import re
import uuid
from fe.access.new_buyer import register_new_buyer
from fe.test.gen_book_data import GenBook
from fe.access.search import Search
import fe.conf
class TestSearch:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.user_id = "test_search_user_id_{}".format(str(uuid.uuid1()))
        self.password = self.user_id
        self.buyer = register_new_buyer(self.user_id, self.password)
        self.store_id = "test_search_store_id_{}".format(str(uuid.uuid1()))
        self.seller_id = "test_search_seller_id_{}".format(str(uuid.uuid1()))
        self.gen_book = GenBook(self.seller_id, self.store_id)
        ok, _ = self.gen_book.blg(non_exist_book_id=False, low_stock_level=False)
        assert ok
        url = fe.conf.URL
        self.search = Search(url_prefix = url)
        yield

    def test_store_title_search_books(self):
        search_parameters = {
            "title": "三毛流浪记全集",
            "scope": self.store_id
        }
        page = 1
        result_per_page = 10
        status_code,response = self.search.search(search_parameters, page, result_per_page)
        
        # check status
        assert status_code == 200
        # check correct response
        assert len(response) != 0
        for result in response:
            pattern = re.compile("三毛流浪记全集")
            assert re.match(pattern, result["title"])
            assert result["store_id"] == self.store_id

    def test_all_search_books(self):
        search_parameters = {
            "title": "三毛流浪记（全集）",
        }
        page = 1
        result_per_page = 10
        status_code, response = self.search.search(search_parameters, page, result_per_page)
        assert status_code == 200
        assert len(response) != 0
        for result in response:
            pattern = re.compile("三毛流浪记（全集）")
            assert re.match(pattern, result["title"])

    def test_store_tags_search_books(self):
        search_parameters = {
            "tags":  ['漫画'],
            "scope": self.store_id
        }
        page = 1
        result_per_page = 10
        status_code,response = self.search.search(search_parameters, page, result_per_page)
        assert status_code == 200
        assert len(response) != 0
        for result in response:
            tag = '漫画'
            print(result)
            assert tag in result["tags"]

    def test_store_content_search_books(self):
        search_parameters = {
            "content": "出版前言",
            "scope": self.store_id
        }
        page = 1
        result_per_page = 10
        status_code, response = self.search.search(search_parameters, page, result_per_page)
        assert status_code == 200
        assert len(response) != 0
        
    

    def test_search_nonexistent_store(self):
        self.store_id = self.store_id + "_x"
        search_parameters = {
            "title": "三毛流浪记（全集）",
            "scope": self.store_id
        }
        page = 1
        result_per_page = 10

        status_code, response = self.search.search(search_parameters, page, result_per_page)

        assert status_code == 513

    def test_empty_search_para(self):
        search_parameters = {}
        page = 1
        result_per_page = 10

        status_code, response = self.search.search(search_parameters, page, result_per_page)
        
        assert status_code == 521