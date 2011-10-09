from parsers.wakaba import Wakaba
from twisted.trial.unittest import TestCase


class TestWakaba(TestCase):

    def setUp(self):
        self.wakaba = Wakaba()

    def test_get_thread_re(self):
        re = self.wakaba.get_thread_re("nyak.ru")
        self.assertIsNotNone(re.match("http://nyak.ru/b/res/1.html"))
        self.assertIsNone(re.match(" http://nyak.ru/b/res/1.html"))
        self.assertIsNone(re.match("http://nyak.ru/b/res/1.html\n"))
        self.assertIsNone(re.match("http://nyak_ru/b/res/1.html"))
        self.assertIsNone(re.match("http://nyak.ru/-/res/1.html"))
        self.assertIsNone(re.match("http://nyak.ru/b/res/12345678901.html"))

    def test_get_board_url(self):
        get_url = self.wakaba.get_board_url
        self.assertEqual(get_url("nyak", "b"), "http://nyak/b/")
        self.assertIsNone(get_url("nyak", ""))
        self.assertIsNone(get_url("nyak", u"\u043d\u044f\u043a"))
        self.assertIsNone(get_url("nyak", "12345678901"))

    def test_get_subscription_username(self):
        get_username = self.wakaba.get_subscription_username
        self.assertEqual(get_username({"type": "nyak"}), "main")
        sub = {"type": "thread_updates", "url": "http://nyak.ru/b/res/1.html"}
        self.assertEqual(get_username(sub), "nyak.ru_b_1")
