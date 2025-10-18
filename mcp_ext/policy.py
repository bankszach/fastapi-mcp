from typing import TypedDict, Literal, List

SideEffect = Literal['read','write','network','exec']
Scope = Literal['vector:write','doc:read','health:read']

class ToolPolicy(TypedDict, total=False):
    sideEffects: List[SideEffect]
    scopes: List[Scope]
    dangerous: bool

POLICY: dict[str, ToolPolicy] = {
    "health.check": {"sideEffects": ["read"], "scopes": ["health:read"]},
    "echo.json": {"sideEffects": ["read"], "scopes": ["health:read"]},
    "index.upsert.v1": {"sideEffects": ["write"], "scopes": ["vector:write","doc:read"], "dangerous": False}
}

def get_policy(tool_name: str) -> ToolPolicy | None:
    return POLICY.get(tool_name)
