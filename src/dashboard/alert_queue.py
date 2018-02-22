"""Manages a list of dismissable alerts."""
import time
import uuid


def _index_matching_predicate(seq, pred):
    """Return index of first item matching predicate.

    Args:
        seq - a list.
        pred - a function with one argument, returning True or False.

    Returns:
        index or None
    """
    for i, v in enumerate(seq):
        if pred(v):
            return i
    return None


class Alert:
    """Represents a dismissable alert."""
    # Alert type constants
    SUCCESS = 'success'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'

    def __init__(self, alert_id, type, title, message, expiration_ts=None):
        """Constructor"""
        self.alert_id = alert_id
        self.type = type
        self.title = title
        self.message = message
        self.expiration_ts = expiration_ts

    def expired_at_time(self, t):
        """Is alert expired."""
        if self.expiration_ts is None:
            return False
        else:
            return self.expiration_ts < t


class AlertQueue:
    def __init__(self):
        """Constructor"""
        self._alerts = []

    def remove_expired(self):
        """Removes the first expired alert, if any."""
        now = time.time()
        index = _index_matching_predicate(self._alerts, lambda a: a.expired_at_time(now))
        if not index is None:
            del self._alerts[index]

    def get_alerts(self):
        """Get list of alerts."""
        self.remove_expired()
        return self._alerts

    def add_alert(self, type, title, message, expiration_seconds=None):
        """Add a new alert to the queue.

        Args:
            type (string) - The alert type.  One of {Alert.SUCCESS, Alert.INFO, Alert.WARNING, Alert.ERROR}
            title (string) - The alert title.
            message (string) - The message to show to the user.
            expiration_seconds (number) - The number of seconds to keep the alert.  If None, alert does not expire.

        Returns:
            A new immutable Alert object.
        """
        alert_id = uuid.uuid4().hex
        expiration_ts = None
        if expiration_seconds:
            expiration_ts = time.time() + expiration_seconds
        new_alert = Alert(alert_id, type, title, message, expiration_ts=expiration_ts)
        self._alerts.append(new_alert)
        return new_alert

    def remove_alert(self, alert_id):
        """Remove alert with the specified id from queue."""
        index = _index_matching_predicate(self._alerts, lambda a: a.alert_id == alert_id)
        if not index is None:
            del self._alerts[index]
