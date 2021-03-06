import os
import time
import logging

import inspect
import pkg_resources

from twisted.python import log

# from scrapy.conf import settings
from scrapy.utils.project import get_project_settings
from scrapy.http import Request, Headers  # noqa
from scrapy.utils.reqser import request_to_dict, request_from_dict  # noqa
from scrapy.responsetypes import responsetypes

import sentry_sdk

SENTRY_DSN = os.environ.get("SENTRY_DSN", None)

settings = get_project_settings()

def get_client(dsn=None, **options):
    """gets a scrapy client"""
    sentry_sdk.init(dsn, **options)


def get_release(crawler):
    """gets the release from a given crawler"""
    try:
        mod = inspect.getmodule(crawler.spidercls)
        pkg = mod.__package__.replace(".", "-")
        return pkg_resources.get_distribution(pkg).version
    except Exception:
        return None


def init(dsn=None):
    """Redirect Scrapy log messages to standard Python logger"""

    # Not needed since scrapy moved to using built-in python logging
    pass


def response_to_dict(response, spider, include_request=True, **kwargs):
    """Returns a dict based on a response from a spider"""
    d = {
        'time': time.time(),
        'status': response.status,
        'url': response.url,
        'headers': dict(response.headers),
        'body': response.body,
    }
    if include_request:
        d['request'] = request_to_dict(response.request, spider)
    return d


def response_from_dict(response, spider=None, **kwargs):
    """Returns a dict based on a response from a spider"""
    url = response.get("url")
    status = response.get("status")
    headers = Headers([(x, list(map(str, y))) for x, y in
                       response.get("headers").items()])
    body = response.get("body")

    respcls = responsetypes.from_args(headers=headers, url=url)
    response = respcls(url=url, headers=headers, status=status, body=body)
    return response
