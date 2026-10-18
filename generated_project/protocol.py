"""Shared wire protocol for the remote command management system.

Messages are JSON objects prefixed by a 4-byte big-endian length header so
arbitrary-sized payloads can be sent reliably over a TCP stream.
"""

import json
import socket
import struct

HEADER_SIZE = 4
HEADER_FORMAT = "!I"


class ProtocolError(Exception):
    """Raised when a malformed frame is received."""


def encode(msg: dict) -> bytes:
    data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    return struct.pack(HEADER_FORMAT, len(data)) + data


def send_msg(sock: socket.socket, msg: dict) -> None:
    """Serialize *msg* and send it over *sock*."""
    sock.sendall(encode(msg))


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed by peer")
        buf.extend(chunk)
    return bytes(buf)


def recv_msg(sock: socket.socket) -> dict:
    """Read exactly one JSON message from *sock*."""
    header = _recv_exact(sock, HEADER_SIZE)
    try:
        size = struct.unpack(HEADER_FORMAT, header)[0]
    except struct.error as exc:  # pragma: no cover
        raise ProtocolError(f"Invalid header: {header!r}") from exc

    if size == 0:  # pragma: no cover
        raise ProtocolError("Received empty message payload")

    try:
        payload = json.loads(_recv_exact(sock, size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise ProtocolError("Message payload must be a JSON object")
    return payload
