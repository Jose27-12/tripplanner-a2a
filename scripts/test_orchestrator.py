"""Prueba del canal 2: HTTP streaming directo a AgentCore con token de Cognito.

Hace lo mismo que hará el navegador:
  1. Obtiene un Access Token de Cognito (usuario de prueba nuevo, o uno existente).
  2. POST al endpoint de invocación del OrchestratorAgent con
     Authorization: Bearer <token> (sin credenciales AWS en la petición).
  3. Lee la respuesta en streaming (SSE) e imprime el texto según llega.

Uso:
  python -X utf8 scripts/test_orchestrator.py "¿Qué viajes tengo guardados?"
  python -X utf8 scripts/test_orchestrator.py --session <id> "Sí, créalo"
  python -X utf8 scripts/test_orchestrator.py --no-token "hola"   # debe dar 401

Requiere credenciales AWS locales solo para crear/confirmar el usuario de
prueba en Cognito (admin), nunca para invocar al agente.
"""
import argparse
import json
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = json.loads((ROOT / "backend" / "stack-outputs.json").read_text(encoding="utf-8"))
REGION = OUTPUTS["Region"]
POOL_ID = OUTPUTS["UserPoolId"]
CLIENT_ID = OUTPUTS["UserPoolClientId"]

ORCHESTRATOR_ARN = "arn:aws:bedrock-agentcore:us-east-1:740314716244:runtime/TripPlannerA2A_OrchestratorAgent-TdSw8JFD6D"
ENDPOINT = (
    f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/"
    f"{urllib.parse.quote(ORCHESTRATOR_ARN, safe='')}/invocations?qualifier=DEFAULT"
)
TEST_PASSWORD = "Test1234!"


def get_access_token(email: str | None) -> tuple[str, str]:
    cognito = boto3.client("cognito-idp", region_name=REGION)
    if email is None:
        email = f"agent-test-{random.randint(10**8, 10**9)}@tripplanner.dev"
        cognito.sign_up(ClientId=CLIENT_ID, Username=email, Password=TEST_PASSWORD)
        cognito.admin_confirm_sign_up(UserPoolId=POOL_ID, Username=email)
    auth = cognito.admin_initiate_auth(
        UserPoolId=POOL_ID,
        ClientId=CLIENT_ID,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": email, "PASSWORD": TEST_PASSWORD},
    )
    return email, auth["AuthenticationResult"]["AccessToken"]


def stream(prompt: str, token: str | None, session_id: str) -> int:
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps({"prompt": prompt}).encode(), headers=headers, method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as err:
        print(f"HTTP {err.code}: {err.read().decode(errors='replace')[:500]}")
        return err.code

    print(f"HTTP {resp.status} — streaming:\n")
    tools_used = []
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            print(data, end="", flush=True)
            continue
        if isinstance(event, str):
            print(event, end="", flush=True)
            continue
        if "error" in event:
            print(f"\n[ERROR] {event['error']}")
            continue
        inner = event.get("event", {})
        delta = inner.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            print(delta["text"], end="", flush=True)
        start = inner.get("contentBlockStart", {}).get("start", {})
        if "toolUse" in start:
            name = start["toolUse"].get("name")
            tools_used.append(name)
            print(f"\n  [tool → {name}]\n", flush=True)
    print(f"\n\n--- fin del stream. Tools usadas: {tools_used or 'ninguna'}")
    return resp.status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--email", help="usuario existente (contraseña de prueba)")
    parser.add_argument("--session", help="session id para continuar una conversación")
    parser.add_argument("--no-token", action="store_true", help="invocar sin token (espera 401)")
    args = parser.parse_args()

    session_id = args.session or f"test-session-{uuid.uuid4()}"
    token = None
    if not args.no_token:
        email, token = get_access_token(args.email)
        print(f"Usuario: {email}")
    print(f"Sesión:  {session_id}")
    status = stream(args.prompt, token, session_id)
    sys.exit(0 if status == 200 or (args.no_token and status in (401, 403)) else 1)


if __name__ == "__main__":
    main()
