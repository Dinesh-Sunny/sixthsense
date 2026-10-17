#!/usr/bin/env bash
# headersHelper for the "example-http-dynamic-auth" server in .mcp.json.
# Must print a JSON object of headers on stdout. Runs at connection time.
# TODO(stub): fetch a short-lived token from your SSO / vault / CLI.
token="${INTERNAL_MCP_TOKEN:-replace-me}"
jq -n --arg t "$token" '{Authorization: ("Bearer " + $t)}'
