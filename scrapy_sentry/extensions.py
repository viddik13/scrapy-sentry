"""
Send signals to Sentry

Use SENTRY_DSN setting to enable sending information
"""
from __future__ import absolute_import, unicode_literals

import os
import logging
import importlib

from scrapy import signals
from scrapy.exceptions import NotConfigured
from six import StringIO
import sentry_sdk

from .utils import init, get_client, get_release, response_to_dict


class Log(object):
    def __init__(self, dsn=None, *args, **kwargs):
        init(dsn)

    @classmethod
    def from_crawler(cls, crawler):
        dsn = crawler.settings.get("SENTRY_DSN", None)
        additional_opts = crawler.settings.get("SENTRY_CLIENT_OPTIONS", {})
        if dsn is None:
            raise NotConfigured('No SENTRY_DSN configured')
        o = cls(dsn=dsn, **additional_opts)
        return o


class Signals(object):
    def __init__(self, client=None, dsn=None, **kwargs):
        get_client(dsn)

    @classmethod
    def from_crawler(cls, crawler, client=None, dsn=None):
        dsn = crawler.settings.get("SENTRY_DSN", None)
        additional_opts = crawler.settings.get("SENTRY_CLIENT_OPTIONS", {})
        o = cls(dsn=dsn,**additional_opts)

        sentry_signals = crawler.settings.get("SENTRY_SIGNALS", [])
        if len(sentry_signals):
            receiver = o.signal_receiver
            for signalname in sentry_signals:
                signal = getattr(signals, signalname)
                crawler.signals.connect(receiver, signal=signal)

        return o

    def signal_receiver(self, signal=None, sender=None, *args, **kwargs):
        message = signal
        extra = {
            'sender': sender,
            'signal': signal,
            'args': args,
            'kwargs': kwargs,
        }
        with sentry_sdk.push_scope() as scope:
            for k, v in extra.iteritems():
                scope.set_extra(k,v)
            sentry_sdk.capture_message(message)
        ident = sentry_sdk.last_event_id()
        return ident


class Errors(object):
    def __init__(self, dsn=None, client=None, **kwargs):
        get_client(dsn, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, client=None, dsn=None):
        release = crawler.settings.get("RELEASE", get_release(crawler))
        additional_opts = crawler.settings.get("SENTRY_CLIENT_OPTIONS", {})

        dsn = os.environ.get(
            "SENTRY_DSN", crawler.settings.get("SENTRY_DSN", None))
        if dsn is None:
            raise NotConfigured('No SENTRY_DSN configured')
        o = cls(dsn=dsn, release=release, **additional_opts)

        sentry_signals = crawler.settings.get("SENTRY_SIGNALS", [])
        if len(sentry_signals)>0:
            receiver = o.spider_error
            for signalpath in sentry_signals:
                signalmodule, signalname = signalpath.rsplit('.', 1)
                _m = importlib.import_module(signalmodule)
                signal = getattr(_m, signalname)
                crawler.signals.connect(receiver, signal=signal)
        else:
            crawler.signals.connect(o.spider_error, signal=signals.spider_error)
        return o

    def spider_error(self, failure, response, spider,
                     signal=None, sender=None,  scope_tags=None, scope_extra=None, scope_level='error',
                     *args, **kwargs):
        # traceback = StringIO()
        err = failure.value
        res_dict = response_to_dict(response, spider, include_request=True)

        extra = {
            'sender': sender,
            'spider': spider.name,
            'signal': signal,
            'failure': failure,
            'response': res_dict,
            'traceback': failure.getTraceback(),
        }
        tags = {}
        if scope_tags is not None:
            tags.update(scope_tags)
        if scope_extra is not None:
            extra.update(scope_extra)
        with sentry_sdk.push_scope() as scope:
            for _k, _v in extra.iteritems():
                scope.set_extra(_k, _v)
            for _k, _v in tags.iteritems():
                scope.set_tag(_k, _v)
            scope.level = scope_level
            sentry_sdk.capture_exception((type(err), err, failure.getTracebackObject()))

        ident = sentry_sdk.last_event_id()
        logging.log(logging.WARNING, "Sentry Exception ID '%s'" % ident)

        return ident
