"""Regression checks that never attempt real network access."""

import socket

import pytest
from pytest_socket import SocketBlockedError


@pytest.mark.parametrize("family", [socket.AF_INET, socket.AF_INET6])
def test_network_socket_creation_blocked(family):
    with pytest.raises(SocketBlockedError):
        socket.socket(family)


@pytest.mark.parametrize(
    "name,args",
    [
        ("getaddrinfo", ("example.org", 443)),
        ("gethostbyname", ("example.org",)),
        ("gethostbyname_ex", ("example.org",)),
        ("gethostbyaddr", ("192.0.2.1",)),
    ],
)
def test_dns_blocked(name, args):
    with pytest.raises(AssertionError, match="mock DNS"):
        getattr(socket, name)(*args)


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="Unix sockets unavailable")
def test_local_socketpair():
    left, right = socket.socketpair(socket.AF_UNIX)
    try:
        left.sendall(b"ok")
        assert right.recv(2) == b"ok"
    finally:
        left.close()
        right.close()
