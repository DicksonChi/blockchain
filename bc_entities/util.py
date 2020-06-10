import json
from hashlib import sha256
from datetime import date, datetime


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def compute_hash(obj):
    """
    Returns the hash of an instance by first converting it
    into JSON string.
    """

    block_string = json.dumps(obj.__dict__, sort_keys=True, default=json_serial)
    return sha256(block_string.encode()).hexdigest()
