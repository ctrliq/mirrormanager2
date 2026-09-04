"""
mirrormanager2 tests for the notification helpers.
"""

from unittest.mock import Mock, patch

from fedora_messaging.exceptions import ConnectionException, PublishReturned
from fedora_messaging.message import Message

from mirrormanager2.lib.notifications import fedmsg_publish


def test_fedmsg_publish_success():
    """A successful publish just delegates to fedora_messaging."""
    msg = Message(topic="test.topic", body={})
    with patch("mirrormanager2.lib.notifications.fm_publish") as fm_publish:
        fedmsg_publish(msg)
    fm_publish.assert_called_once_with(msg)


def test_fedmsg_publish_swallows_connection_errors():
    """A broker that's still unreachable after retries must not raise out of
    fedmsg_publish. Patches past the retry decorator so the test doesn't pay
    for the real backoff delay."""
    msg = Message(topic="test.topic", body={})
    with patch(
        "mirrormanager2.lib.notifications._fedmsg_publish",
        Mock(side_effect=ConnectionException("no broker")),
    ):
        fedmsg_publish(msg)  # should not raise


def test_fedmsg_publish_swallows_publish_errors():
    """A broker-side rejection (not retried) must not raise out of
    fedmsg_publish either."""
    msg = Message(topic="test.topic", body={})
    with patch(
        "mirrormanager2.lib.notifications.fm_publish",
        Mock(side_effect=PublishReturned("rejected")),
    ):
        fedmsg_publish(msg)  # should not raise
