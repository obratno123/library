from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from support_chat.routing import websocket_urlpatterns


class SupportChatRoutingTest(SimpleTestCase):
    def setUp(self):
        self.pattern = websocket_urlpatterns[0]

    def test_support_chat_websocket_url_resolves(self):
        match = self.pattern.resolve("ws/support-chat/123/")

        self.assertIsNotNone(match)
        self.assertEqual(match.kwargs["dialog_id"], "123")

    def test_support_chat_websocket_url_does_not_resolve_without_id(self):
        match = self.pattern.resolve("ws/support-chat/")

        self.assertIsNone(match)

    def test_support_chat_websocket_url_does_not_resolve_with_non_numeric_id(self):
        match = self.pattern.resolve("ws/support-chat/abc/")

        self.assertIsNone(match)

    def test_support_chat_websocket_url_does_not_resolve_without_trailing_slash(self):
        match = self.pattern.resolve("ws/support-chat/123")

        self.assertIsNone(match)