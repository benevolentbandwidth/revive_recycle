"""Block DNS as well as the sockets disabled by pytest-socket."""

import socket

import pytest


@pytest.fixture(autouse=True)
def forbid_dns(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must mock DNS; external network and paid APIs are forbidden")

    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
        monkeypatch.setattr(socket, name, blocked)
