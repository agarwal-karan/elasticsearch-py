try:
    import simplejson as json
except ImportError:
    import json
import decimal
from bson import ObjectId
from datetime import date, datetime, time
from decimal import Decimal

from .exceptions import SerializationError, ImproperlyConfigured
from .compat import string_types

class TextSerializer(object):
    mimetype = 'text/plain'

    def loads(self, s):
        return s

    def dumps(self, data):
        if isinstance(data, string_types):
            return data

        raise SerializationError('Cannot serialize %r into text.' % data)

def is_aware(value):
    """
    Determines if a given datetime.datetime is aware.
    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

class JSONSerializer(object):
    mimetype = 'application/json'

    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, date):
            return o.isoformat()
        elif isinstance(o, time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, ObjectId):
            return str(o)
        raise TypeError("Unable to serialize %r (type: %s)" % (o, type(o)))

    def loads(self, s):
        try:
            return json.loads(s)
        except (ValueError, TypeError) as e:
            raise SerializationError(s, e)

    def dumps(self, data):
        # don't serialize strings
        if isinstance(data, string_types):
            return data

        try:
            return json.dumps(data, default=self.default)
        except (ValueError, TypeError) as e:
            raise SerializationError(data, e)

DEFAULT_SERIALIZERS = {
    JSONSerializer.mimetype: JSONSerializer(),
    TextSerializer.mimetype: TextSerializer(),
}

class Deserializer(object):
    def __init__(self, serializers, default_mimetype='application/json'):
        try:
            self.default = serializers[default_mimetype]
        except KeyError:
            raise ImproperlyConfigured('Cannot find default serializer (%s)' % default_mimetype)
        self.serializers = serializers

    def loads(self, s, mimetype=None):
        if not mimetype:
            deserializer = self.default
        else:
            # split out charset
            mimetype = mimetype.split(';', 1)[0]
            try:
                deserializer = self.serializers[mimetype]
            except KeyError:
                raise SerializationError('Unknown mimetype, unable to deserialize: %s' % mimetype)

        return deserializer.loads(s)

