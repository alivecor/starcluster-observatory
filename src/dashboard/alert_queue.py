"""Manages a list of dismissable alerts."""
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
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'

    def __init__(self, alert_id, type, message):
        """Constructor"""
        self.alert_id = alert_id
        self.type = type
        self.message = message


class AlertQueue:
    def __init__(self):
        """Constructor"""
        self._alerts = []

    def get_alerts(self):
        """Get list of alerts."""
        return self._alerts

    def add_alert(self, type, message):
        """Add a new alert to the queue.

        Args:
            type (string) - The alert type.  One of {Alert.INFO, Alert.WARNING, Alert.ERROR}
            message (string) - The message to show to the user.

        Returns:
            A new immutable Alert object.
        """
        alert_id = uuid.uuid4().hex
        new_alert = Alert(alert_id, type, message)
        self._alerts.append(new_alert)
        return new_alert

    def remove_alert(self, alert_id):
        """Remove alert with the specified id from queue."""
        index = _index_matching_predicate(self._alerts, lambda a: a.alert_id == alert_id)
        if index:
            del self._alerts[index]
