import argparse
import base64
import json
from typing import Any, Dict

from exodus.server.exodus_executor_client import ExodusExecutorClient


def base64_json(s: str) -> Dict[str, Any]:
    try:
        decoded_data = base64.b64decode(s).decode("utf-8")
        return json.loads(decoded_data)
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Invalid base64 JSON: {e}")


def main():
    parser = argparse.ArgumentParser(prog="EXODUS Client CLI")
    parser.add_argument("--tool-name", required=True, type=str)
    parser.add_argument("--tool-args-b64", required=True, type=base64_json)
    args = parser.parse_args()

    tool_name = args.tool_name
    tool_args = args.tool_args_b64
    exodus_client = ExodusExecutorClient()
    command_result = exodus_client.execute_tool(tool_name=tool_name, tool_args=tool_args)
    print(command_result)


if __name__ == "__main__":
    main()
