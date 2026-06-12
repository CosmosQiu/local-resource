"""
Cookie expiry detection — scheduled Celery task.

For each active AIAccount that has cookie_data, this task:
1. Sends a request to the corresponding platform endpoint using the stored cookies
2. Parses the response to detect expiry / remaining days
3. Updates the account's expiration_date, last_verified_at, and status

Supported platforms are defined in PLATFORM_CHECK_CONFIG.
"""
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import async_session
from app.core.security import decrypt_secret
from app.models.account import AIAccount

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-platform cookie check configuration
# Each entry: URL to hit + a parser function
# ---------------------------------------------------------------------------
PLATFORM_CHECK_CONFIG: dict[str, dict] = {
    "openai": {
        "url": "https://api.openai.com/dashboard/billing/subscription",
        "method": "GET",
        "parser": "parse_openai",
    },
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "method": "GET",
        "parser": "parse_claude",
    },
    "deepseek": {
        "url": "https://api.deepseek.com/user/balance",
        "method": "GET",
        "parser": "parse_json_expiry",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "method": "GET",
        "parser": "parse_json_expiry",
    },
}


def parse_openai(response: httpx.Response) -> tuple[bool, str | None, datetime | None]:
    """Parse OpenAI billing subscription response."""
    try:
        data = response.json()
        # OpenAI returns access_until as a Unix timestamp
        access_until = data.get("access_until")
        if access_until:
            expiry = datetime.fromtimestamp(access_until, tz=timezone.utc)
            return True, None, expiry
        # Fallback: check if the account has hard limits
        hard_limit_usd = data.get("hard_limit_usd")
        if hard_limit_usd is not None and hard_limit_usd <= 0:
            return False, "Hard limit exhausted", None
        return True, None, None
    except Exception as e:
        return False, str(e), None


def parse_claude(response: httpx.Response) -> tuple[bool, str | None, datetime | None]:
    """Parse Claude/Anthropic response."""
    if response.status_code == 401:
        return False, "Unauthorized — API key likely expired", None
    if response.status_code == 403:
        return False, "Forbidden — account may be suspended", None
    if response.status_code == 429:
        return False, "Rate limited — check billing status", None
    return True, None, None


def parse_json_expiry(response: httpx.Response) -> tuple[bool, str | None, datetime | None]:
    """Generic parser: look for expiration/expiry fields in JSON."""
    try:
        data = response.json()
        # Try common expiry field names
        for field in ("expires_at", "expiration_date", "valid_until", "expiry"):
            val = data.get(field)
            if isinstance(val, (int, float)):
                return True, None, datetime.fromtimestamp(val, tz=timezone.utc)
            if isinstance(val, str):
                try:
                    return True, None, datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return True, None, None
    except Exception as e:
        return False, str(e), None


PARSER_MAP = {
    "parse_openai": parse_openai,
    "parse_claude": parse_claude,
    "parse_json_expiry": parse_json_expiry,
}


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------
@celery_app.task(name="app.tasks.cookie_checker.verify_all_account_cookies")
def verify_all_account_cookies():
    """Verify all active accounts that have cookie_data configured."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(_async_verify_all())


async def _async_verify_all():
    async with async_session() as db:
        result = await db.execute(
            select(AIAccount).where(
                AIAccount.status.in_(["active", "error"]),
                AIAccount.cookie_data.isnot(None),
            )
        )
        accounts = list(result.scalars().all())

    if not accounts:
        logger.info("No active accounts with cookie data to verify")
        return {"checked": 0, "expired": 0, "errors": 0}

    checked = 0
    expired_count = 0
    error_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for account in accounts:
            try:
                status = await _verify_single_account(client, account)
                checked += 1
                if status == "expired":
                    expired_count += 1
                elif status == "error":
                    error_count += 1
            except Exception as e:
                logger.error(f"Failed to verify account {account.id}: {e}")
                error_count += 1

    logger.info(f"Cookie check done: {checked} checked, {expired_count} expired, {error_count} errors")
    return {"checked": checked, "expired": expired_count, "errors": error_count}


async def _verify_single_account(
    client: httpx.AsyncClient, account: AIAccount
) -> str:
    """Verify a single account. Returns 'ok', 'expired', or 'error'."""
    config = PLATFORM_CHECK_CONFIG.get(account.platform)
    if not config:
        logger.warning(f"No check config for platform {account.platform}")
        return "ok"

    # Decrypt cookie data
    try:
        cookie_raw = decrypt_secret(account.cookie_data) if account.cookie_data else None
    except Exception:
        logger.error(f"Failed to decrypt cookie_data for account {account.id}")
        return "error"

    if not cookie_raw:
        return "ok"

    try:
        cookies = json.loads(cookie_raw)
    except json.JSONDecodeError:
        cookies = {}

    # Send request with stored cookies
    try:
        response = await client.request(
            method=config["method"],
            url=config["url"],
            cookies=cookies,
        )
    except httpx.RequestError as e:
        await _update_verification(account, success=False, error=str(e))
        return "error"

    # Parse response
    parser_name = config["parser"]
    parser = PARSER_MAP.get(parser_name, parse_json_expiry)
    success, error_msg, expiry = parser(response)

    await _update_verification(
        account,
        success=success,
        error=error_msg,
        expiry=expiry,
    )

    if not success:
        return "error"
    if expiry and expiry < datetime.now(timezone.utc):
        return "expired"
    return "ok"


async def _update_verification(
    account: AIAccount,
    success: bool,
    error: str | None = None,
    expiry: datetime | None = None,
):
    """Update account verification status in DB."""
    async with async_session() as db:
        result = await db.execute(select(AIAccount).where(AIAccount.id == account.id))
        acc = result.scalar_one_or_none()
        if not acc:
            return

        acc.last_verified_at = datetime.now(timezone.utc)

        if success:
            acc.verification_error = None
            if expiry:
                acc.expiration_date = expiry
                if expiry < datetime.now(timezone.utc) and acc.status == "active":
                    acc.status = "expired"
            else:
                # Account is OK — if it was in error state, recover to active
                if acc.status == "error":
                    acc.status = "active"
        else:
            acc.verification_error = error
            if acc.status == "active":
                acc.status = "error"

        await db.commit()
