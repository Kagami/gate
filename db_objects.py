import datetime
from twisted.internet import defer
import txmongo
from txmongo.filter import ASCENDING, DESCENDING
import db


class UserSettings(db.MongoObject):
    
    collection_name = "users_settings"
    indexes = (
        (ASCENDING("jid"), True),
    )

    def __init__(self, jid):
        self._jid = jid

    @defer.inlineCallbacks
    def is_exists(self):
        """If user doesn't exist, set initial settings."""
        time = datetime.datetime.utcfromtimestamp(0)
        try:
            res = yield self._db.insert(
                {"jid": self._jid, "last_subscribe": time},
                safe=True)
        except txmongo._pymongo.errors.OperationFailure:
            defer.returnValue(True)
        else:
            defer.returnValue(False)

    @defer.inlineCallbacks
    def is_too_fast_subscribe(self):
        """Return False and update user's last
        subscribe time to now if last subscribe
        was more than second ago.
        Else return True that means it's too fast to
        subscribe now.
        """
        now = datetime.datetime.utcnow()
        second_ago = now - datetime.timedelta(seconds=1)
        try:
            yield self._db.update(
                {"jid": self._jid, "last_subscribe": {"$lte": second_ago}},
                {"$set": {"last_subscribe": now}},
                upsert=True, safe=True)
        except txmongo._pymongo.errors.OperationFailure:
            defer.returnValue(True)
        else:
            defer.returnValue(False)


class UserSubscriptions(db.MongoObject):
    """User's url subscriptions.
    User identified by his jid.
    """

    collection_name = "users_subscriptions"
    indexes = (
        (ASCENDING(("jid", "url")), True),
        (ASCENDING("url"), False),
    )

    def __init__(self, jid):
        self._jid = jid

    @defer.inlineCallbacks
    def is_subscribed(self, url):
        """Is user subscribed to this url."""
        res = yield self._db.find_one(
            {"jid": self._jid, "url": url},
            fields=[])
        defer.returnValue(bool(res))

    def subscribe(self, url):
        return self._db.insert(
            {"jid": self._jid, "url": url})

    def unsubscribe(self, url):
        return self._db.remove(
            {"jid": self._jid, "url": url})

    @classmethod
    def unsubscribe_all(cls, url):
        return cls._db.remove(
            {"url": url})

    def get_list(self):
        """Return user's subscriptions."""
        return self._db.find(
            {"jid": self._jid},
            fields=["url", "description"])

    @classmethod
    def find(cls, url):
        """Return users subscribed to given url."""
        return cls._db.find(
            {"url": url},
            fields=["jid"])


class Subscription(db.MongoObject):
    """List of all users subscriptions.
    Url should be unique field.
    Fetchers and parsers use this class
    for processing subscriptions.
    """

    collection_name = "subscriptions"
    indexes = (
        (ASCENDING("url"), True),
        (ASCENDING("jid"), False),
    )

    def __init__(self, url):
        self._url = url

    @classmethod
    def create(cls, sub):
        return cls._db.insert(sub)

    def remove(self):
        return self._db.remove(
            {"url": self._url})

    @defer.inlineCallbacks
    def remove_empty(self):
        """Remove subscription if it has no
        subscribers.
        """
        coll_name = UserSubscriptions.collection_name
        subscriber_exists = yield self._all_db(coll_name).find_one(
            {"url": self._url},
            fields=[])
        if not subscriber_exists:
            yield self._db.remove({"url": self._url})

    @classmethod
    def get_list(cls):
        """All subscriptions."""
        return cls._db.find()

    @defer.inlineCallbacks
    def get_last_modified(self):
        res = yield self._db.find_one(
            {"url": self._url},
            fields=["last_modified"])
        if "last_modified" in res:
            defer.returnValue(res["last_modified"])

    def set_last_modified(self, last_modified):
        return self._db.update(
            {"url": self._url},
            {"$set": {"last_modified": last_modified}})

    @defer.inlineCallbacks
    def get_last(self):
        res = yield self._db.find_one(
            {"url": self._url},
            fields=["last"])
        if res:
            defer.returnValue(res["last"])

    def set_last(self, last):
        return self._db.update(
            {"url": self._url},
            {"$set": {"last": last}})

    @classmethod
    @defer.inlineCallbacks
    def is_jid_exists(cls, jid):
        res = yield cls._db.find_one(
            {"jid": jid},
            fields=[])
        defer.returnValue(bool(res))

    @defer.inlineCallbacks
    def get_jid(self):
        res = yield self._db.find_one(
            {"url": self._url},
            fields=["jid"])
        if res:
            defer.returnValue(res["jid"])

    @classmethod
    @defer.inlineCallbacks
    def get_url_by_jid(cls, jid):
        res = yield cls._db.find_one(
            {"jid": jid},
            fields=["url"])
        if res:
            defer.returnValue(res["url"])


class Host(db.MongoObject):
    """Host settings."""

    collection_name = "hosts"
    indexes = (
        (ASCENDING("host"), True),
    )

    def __init__(self, host):
        self._host = host

    @defer.inlineCallbacks
    def is_too_fast(self):
        """Return False and update host's last use time
        to now if last use was more than second ago.
        Else return True that means it's too fast to
        use host now.
        """
        now = datetime.datetime.utcnow()
        second_ago = now - datetime.timedelta(seconds=1)
        try:
            yield self._db.update(
                {"host": self._host, "last_use": {"$lte": second_ago}},
                {"$set": {"last_use": now}},
                upsert=True, safe=True)
        except txmongo._pymongo.errors.OperationFailure:
            defer.returnValue(True)
        else:
            defer.returnValue(False)

    @defer.inlineCallbacks
    def inc_errors(self):
        """Increment host errors and return
        errors count.
        """
        yield self._db.update(
            {"host": self._host},
            {"$inc": {"errors": 1}})
        res = yield self._db.find_one(
            {"host": self._host},
            fields=["errors"])
        defer.returnValue(res["errors"])
