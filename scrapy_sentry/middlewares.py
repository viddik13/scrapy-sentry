from __future__ import absolute_import

import os
import sys
import logging

from scrapy.exceptions import NotConfigured
import sentry_sdk

from .utils import get_client


class SentryMiddleware(object):
    def __init__(self, dsn=None, client=None):
        get_client(dsn)

    @classmethod
    def from_crawler(cls, crawler):
        dsn = os.environ.get(
            "SENTRY_DSN", crawler.settings.get("SENTRY_DSN", None))
        if dsn is None:
            raise NotConfigured('No SENTRY_DSN configured')
        return cls(dsn)

    def trigger(self, exception, spider=None, extra=None):
        extradata = {}
        if extra is not None:
            extradata.update(extra)
        extradata['spider'] = spider.name if spider else ""
        with sentry_sdk.push_scope() as scope:
            for k, v in extradata.iteritems():
                scope.set_extra(k,v)
            sentry_sdk.capture_exception(sys.exc_info())
        ident = sentry_sdk.last_event_id()
        logging.log(logging.INFO, "Sentry Exception ID '%s'" % ident)
        return None

    def process_exception(self, request, exception, spider):
        return self.trigger(exception, spider,
                            extra={"spider": spider, "request": request})

    def process_spider_exception(self, response, exception, spider):
        return self.trigger(exception, spider,
                            extra={"spider": spider, "response": response})
