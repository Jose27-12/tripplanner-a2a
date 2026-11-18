"""Cliente DynamoDB compartido entre todas las Lambdas."""
import os
import boto3
from boto3.dynamodb.conditions import Key

_TABLE_NAME = os.environ["TABLE_NAME"]
_dynamodb = boto3.resource("dynamodb")
table = _dynamodb.Table(_TABLE_NAME)


def pk(user_id: str) -> str:
    return f"USER#{user_id}"


def sk_trip(trip_id: str) -> str:
    return f"TRIP#{trip_id}"


def sk_itin(trip_id: str) -> str:
    return f"ITIN#{trip_id}"


def sk_res(res_id: str) -> str:
    return f"RES#{res_id}"


def sk_prefs() -> str:
    return "PREFS"


def sk_profile() -> str:
    return "PROFILE"


def query_by_prefix(user_id: str, prefix: str) -> list:
    """Lista todos los items de un usuario con un prefijo de SK dado."""
    resp = table.query(
        KeyConditionExpression=(
            Key("PK").eq(pk(user_id)) & Key("SK").begins_with(prefix)
        )
    )
    return resp.get("Items", [])


def get_item(user_id: str, sort_key: str) -> dict | None:
    """Obtiene un item por PK+SK. Devuelve None si no existe."""
    resp = table.get_item(Key={"PK": pk(user_id), "SK": sort_key})
    return resp.get("Item")


def query_gsi1(trip_id: str) -> list:
    """Lista reservas de un viaje usando GSI1."""
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression=(
            Key("GSI1PK").eq(f"TRIP#{trip_id}") & Key("GSI1SK").begins_with("RES#")
        ),
    )
    return resp.get("Items", [])
