# -*- coding: utf-8 -*-
"""
Custom exceptions.
"""

class RequestError(Exception):

    def __init__(self, url, code, reason):
        self.url = url
        self.code = code
        self.reason = reason

    def __str__(self):
        return "{reason} ({code}) on {url}".format(
            reason=self.reason, code=self.code, url=self.url)


class WrongContentType(Exception):

    def __init__(self, message, url, content_type):
        self.url = url
        self.content_type = content_type
        super().__init__(message)
