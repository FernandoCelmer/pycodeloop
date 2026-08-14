from __future__ import annotations

from typing import Any

METHOD_NOT_FOUND = -32601
SERVER_ERROR = -32000
CHAT_ALREADY_RUNNING = -32001


def notification(method: str, params: dict) -> dict:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def response(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
