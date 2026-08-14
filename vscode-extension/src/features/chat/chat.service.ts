import { RpcMessage } from "../../core-client/core-client";

export function forwardedEventType(method: string): string {
  return method.replace("chat/", "");
}

export function mapSendResponse(response: RpcMessage): { type: string } & Record<string, unknown> {
  return response.error
    ? { type: "error", message: response.error.message }
    : { type: "done", text: response.result?.text ?? "" };
}

export function mapAskResponse(
  id: string,
  response: RpcMessage
): { type: string } & Record<string, unknown> {
  return response.error
    ? { type: "asideError", id, message: response.error.message }
    : { type: "asideAnswer", id, text: response.result?.text ?? "" };
}
