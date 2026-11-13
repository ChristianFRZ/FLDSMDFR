from datetime import timedelta
from uuid import uuid4

import pytest

from meloxo_common.auth import AuthStateCache, CurrentUser, build_auth
from meloxo_common.config import get_base_settings
from meloxo_common.contracts import AuthState
from meloxo_common.errors import AppError
from meloxo_common.internal import UpstreamError
from meloxo_common.security import encode_token


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x/y")
    monkeypatch.setenv("JWT_SECRET", "secreto-de-prueba-de-32-bytes-o-mas-xx")
    get_base_settings.cache_clear()
    yield
    get_base_settings.cache_clear()


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Origin:
    """Origen falso: cuenta llamadas y permite cambiar el estado o caerse."""

    def __init__(self, state: AuthState | None):
        self.state = state
        self.calls = 0
        self.down = False

    async def __call__(self, user_id):
        self.calls += 1
        if self.down:
            raise UpstreamError()
        return self.state


def _state(role="admin", status="active") -> AuthState:
    return AuthState(id=uuid4(), role=role, status=status)


def _token(state: AuthState, **extra) -> str:
    return encode_token({"sub": str(state.id), **extra}, timedelta(minutes=5))


def _setup(state: AuthState | None):
    origin, clock = Origin(state), Clock()
    auth = build_auth(origin, clock=clock)
    return auth, origin, clock


async def test_state_is_cached_for_30_seconds():
    state = _state()
    origin, clock = Origin(state), Clock()
    cache = AuthStateCache(origin, clock=clock)
    await cache.get(state.id)
    clock.advance(29)
    await cache.get(state.id)
    assert origin.calls == 1
    clock.advance(2)
    await cache.get(state.id)
    assert origin.calls == 2


async def test_suspension_applies_after_ttl():
    state = _state()
    auth, origin, clock = _setup(state)
    token = _token(state)
    assert await auth.resolve_user(token) == CurrentUser(id=state.id, role="admin")
    origin.state = state.model_copy(update={"status": "suspended"})
    clock.advance(31)
    with pytest.raises(AppError) as exc:
        await auth.resolve_user(token)
    assert exc.value.status == 401 and exc.value.code == "invalid_token"


async def test_suspension_not_applied_before_ttl():
    state = _state()
    auth, origin, clock = _setup(state)
    token = _token(state)
    await auth.resolve_user(token)
    origin.state = state.model_copy(update={"status": "suspended"})
    clock.advance(29)
    assert (await auth.resolve_user(token)).id == state.id


async def test_unknown_user_is_rejected():
    auth, _, _ = _setup(None)
    with pytest.raises(AppError) as exc:
        await auth.resolve_user(_token(_state()))
    assert exc.value.status == 401


async def test_stale_state_used_when_origin_down():
    state = _state()
    auth, origin, clock = _setup(state)
    token = _token(state)
    await auth.resolve_user(token)
    origin.down = True
    clock.advance(3600)
    assert (await auth.resolve_user(token)).id == state.id


async def test_cold_cache_and_origin_down_raises_503():
    state = _state()
    auth, origin, _ = _setup(state)
    origin.down = True
    with pytest.raises(UpstreamError) as exc:
        await auth.resolve_user(_token(state))
    assert exc.value.status == 503


async def test_role_change_follows_same_ttl():
    state = _state(role="admin")
    auth, origin, clock = _setup(state)
    token = _token(state)
    assert (await auth.resolve_user(token)).role == "admin"
    origin.state = state.model_copy(update={"role": "listener"})
    clock.advance(29)
    assert (await auth.resolve_user(token)).role == "admin"
    clock.advance(2)
    assert (await auth.resolve_user(token)).role == "listener"


async def test_stream_scope_token_rejected_as_session():
    state = _state()
    auth, origin, _ = _setup(state)
    with pytest.raises(AppError) as exc:
        await auth.resolve_user(_token(state, scope="stream"))
    assert exc.value.status == 401 and exc.value.code == "invalid_token"
    assert origin.calls == 0


async def test_require_role_forbids_other_roles():
    state = _state(role="listener")
    auth, _, _ = _setup(state)
    dependency = auth.require_role("admin")
    with pytest.raises(AppError) as exc:
        await dependency(CurrentUser(id=state.id, role="listener"))
    assert exc.value.status == 403 and exc.value.code == "forbidden"
    admin = CurrentUser(id=state.id, role="admin")
    assert await dependency(admin) == admin
