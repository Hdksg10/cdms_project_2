from pymongo.errors import PyMongoError
from be.model import error
from be.model import db_conn
import re

class Search(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        
    def search(self, parameters, page, result_per_page):
        try:
            book_collection = self.mongo["books"]
            # parse parameters
            store_id = parameters.get("scope", None)
            title = parameters.get("title", None)
            tags = parameters.get("tags", None)
            content = parameters.get("content", None)
            # build query
            condition_list = []
            if store_id is not None:
                if not self.store_id_exist(store_id):
                    return *error.error_non_exist_store_id(store_id), [] 
                condition_list.append({"store_id": store_id})
            if title is not None:
                condition_list.append({"title": re.compile(title)})
            if tags is not None:
                condition_list.append({"tags": {"$in": tags}})
            if content is not None:
                condition_list.append({"$text": {"$search": content}})
            if len(condition_list) == 0:
                return *error.error_empty_search_parameters(), []
            query = {"$and": condition_list}
            results = list(book_collection.find(query, {"_id": 0, "owner": 0, "content_seg": 0}).skip((page - 1) * result_per_page).limit(result_per_page))
            
        except PyMongoError as e:
            print("{}".format(str(e)))
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            print("{}".format(str(e)))
            return 530, "{}".format(str(e)), []
        return 200, "ok", results