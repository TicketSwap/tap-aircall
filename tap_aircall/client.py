"""REST client handling, including AircallStream base class."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import ParseResult, parse_qsl

import requests
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.pagination import BaseHATEOASPaginator
from singer_sdk.streams import RESTStream

_Auth = Callable[[requests.PreparedRequest], requests.PreparedRequest]
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class MyPaginator(BaseHATEOASPaginator):
    """Paginator that follows Aircall's next_page_link."""

    def get_next_url(self, response: requests.Response) -> str | None:
        """Return the next page URL from the response metadata."""
        data = response.json()
        return data.get("meta").get("next_page_link")


class AircallStream(RESTStream):
    """Aircall stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return "https://api.aircall.io/v1"

    records_jsonpath = "$[*]"  # Or override `parse_response`.

    @property
    def authenticator(self) -> BasicAuthenticator:
        """Return the authenticator."""
        return BasicAuthenticator(
            username=self.config.get("api_key"),
            password=self.config.get("api_token"),
        )

    def get_url_params(
        self,
        context: dict | None,
        next_page_token: ParseResult | None,
    ) -> dict[str, Any]:
        """Return the URL params for the request."""
        params: dict[str, Any] = {"per_page": 50}
        start_date = self.get_starting_replication_key_value(context)

        if start_date:
            if isinstance(start_date, str):
                start_date = int(
                    datetime.timestamp(
                        datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S%z"),
                    ),
                )
            params.update({"from": start_date})

        if next_page_token:
            params.update(parse_qsl(next_page_token.query))

        return params

    def get_new_paginator(self) -> BaseHATEOASPaginator:
        """Create a new pagination helper instance.

        If the source API can make use of the `next_page_token_jsonpath`
        attribute, or it contains a `X-Next-Page` header in the response
        then you can remove this method.

        If you need custom pagination that uses page numbers, "next" links, or
        other approaches, please read the guide: https://sdk.meltano.com/en/v0.25.0/guides/pagination-classes.html.

        Returns:
            A pagination helper instance.
        """
        return MyPaginator()
