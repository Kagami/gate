from twisted.internet import defer
import txmongo
import config


class DBConnection(object):
    """Wrapper around MongoConnection."""

    def __init__(self):
        self._conn = None
        self._db = None
        self._deferred = txmongo.MongoConnection()

    @defer.inlineCallbacks
    def _get_conn(self):
        if self._conn is None:
            # Wait for connect.
            # Several clients can wait here so only first
            # get the connection; others get None.
            conn = yield self._deferred
            if conn is not None:
                self._conn = conn
        defer.returnValue(self._conn)

    # TODO: Auth? Currently there is no authorization
    # support in the txmongo package.
    @defer.inlineCallbacks
    def get_db(self, collection=""):
        if self._db is None:
            _conn = yield self._get_conn()
            self._db = _conn[config.database_name]

        if collection:
            defer.returnValue(self._db[collection])
        else:
            defer.returnValue(self._db)

db_conn = DBConnection()


class _DBWrapper(object):
    """Implements collection functions which return deferred."""

    def __init__(self, collection_name):
        self.collection_name = collection_name

    def __getattr__(self, db_method):
        def fn(*args, **kwargs):
            d = db_conn.get_db(self.collection_name)
            d.addCallback(
                lambda collection:
                    getattr(collection, db_method)(*args, **kwargs))
            return d
        return fn


class _MongoObjectMeta(type):
    """Metaclass for MongoObject. Initialize wrapper
    (so you can use it even in class methods) and
    create indexes.
    """

    def __init__(cls, name, bases, dct):
        if "collection_name" in dct:
            cls._db = _DBWrapper(dct["collection_name"])
            cls.create_indexes()


class MongoObject(object):
    """Base abstract class for mongo objects."""

    __metaclass__ = _MongoObjectMeta
    indexes = ()

    @staticmethod
    def _all_db(collection_name):
        return _DBWrapper(collection_name)

    @classmethod
    @defer.inlineCallbacks
    def create_indexes(cls):
        for index, unique in cls.indexes:
            sort = txmongo.filter.sort(index)
            yield cls._db.create_index(sort, unique=unique)
