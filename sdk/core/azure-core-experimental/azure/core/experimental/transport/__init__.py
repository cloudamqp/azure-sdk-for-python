# --------------------------------------------------------------------------
#
# Copyright (c) Microsoft Corporation. All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the ""Software""), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
# --------------------------------------------------------------------------
# pylint:disable=undefined-all-variable
from typing import List


__all__ = [
    "PyodideTransport",
    "HttpXTransport",
    "AsyncHttpXTransport",
    "Urllib3Transport",
]


def __dir__() -> List[str]:
    return __all__


def __getattr__(name: str):
    if name == "PyodideTransport":
        try:
            from ._pyodide import PyodideTransport

            return PyodideTransport
        except ImportError as err:
            raise ImportError("pyodide package is not installed") from err
    if name == "HttpXTransport":
        try:
            from ._httpx import HttpXTransport

            return HttpXTransport
        except ImportError as err:
            raise ImportError("httpx package is not installed") from err
    if name == "AsyncHttpXTransport":
        try:
            from ._httpx_async import AsyncHttpXTransport

            return AsyncHttpXTransport
        except ImportError as err:
            raise ImportError("httpx package is not installed") from err
    if name == "Urllib3Transport":
        try:
            from ._urllib3 import Urllib3Transport

            return Urllib3Transport
        except ImportError as err:
            raise ImportError("urllib3 package is not installed") from err
    raise AttributeError(f"module 'azure.core.experimental.transport' has no attribute {name}")
