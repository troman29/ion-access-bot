import asyncio
from collections import Counter
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from itertools import batched
from typing import Any

import aiohttp
from ton_core import Address, PublicKey

from app.storage import TokenData, TokenType

from .models import DEFAULT_DECIMALS, IndexerError, TokenMeta, raw_address

PAGE = 1000
OWNERS_PER_REQUEST = 100
TIMEOUT = aiohttp.ClientTimeout(total=15)
NATIVE_TOKEN_ADDRESS = "ION"
NATIVE_DECIMALS = 9


def ion_equivalent(native_balance: int, lion_balance: int, lion_decimals: int, rate: Decimal) -> int:
    if not rate.is_finite() or rate <= 0:
        raise IndexerError("Invalid LION staking rate")
    numerator, denominator = rate.as_integer_ratio()
    staked = lion_balance * numerator * 10**NATIVE_DECIMALS // (denominator * 10**lion_decimals)
    return native_balance + staked


class Indexer:
    def __init__(self, url: str, staking_api_url: str, lion_jetton: str, key: str | None = None) -> None:
        self.url = url.rstrip("/")
        self.staking_api_url = staking_api_url.rstrip("/")
        self.lion_jetton = raw_address(lion_jetton)
        self.key = key
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(timeout=TIMEOUT)

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        if self.session is None:
            raise IndexerError("Indexer session is not started")
        headers = {"X-Api-Key": self.key} if self.key and url.startswith(self.url) else {}
        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            raise IndexerError(f"ION API request failed: {url}") from error
        if not isinstance(data, dict):
            raise IndexerError(f"ION API returned an invalid response: {url}")
        return data

    async def _indexer(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", f"{self.url}/indexer/v3{path}", params=params)

    async def resolve_token(self, address: str) -> TokenMeta | None:
        raw = raw_address(address)
        data = await self._indexer("/jetton/masters", {"address": address})
        masters = data.get("jetton_masters")
        if not isinstance(masters, list):
            raise IndexerError("ION indexer returned no jetton master list")
        master = next((item for item in masters if raw_address(item["address"]) == raw), None)
        if master is None:
            return None
        metadata = data.get("metadata", {}).get(master["address"], {})
        info = (metadata.get("token_info") or [{}])[0]
        content = master.get("jetton_content") or {}
        decimals = info.get("extra", {}).get("decimals", content.get("decimals", DEFAULT_DECIMALS))
        try:
            decimals = int(decimals)
        except (TypeError, ValueError) as error:
            raise IndexerError("Invalid jetton decimals") from error
        if not 0 <= decimals <= 255:
            raise IndexerError("Invalid jetton decimals")
        name = info.get("name") or content.get("name") or info.get("symbol") or "Unknown jetton"
        return TokenMeta(TokenType.JETTON, name, address, decimals)

    async def _jetton_balances(self, masters: list[str], owners: list[str]) -> Counter[tuple[str, str]]:
        found: Counter[tuple[str, str]] = Counter()
        seen: set[str] = set()
        offset = 0
        while True:
            data = await self._indexer("/jetton/wallets", {
                "owner_address": owners,
                "jetton_address": masters,
                "exclude_zero_balance": "true",
                "limit": PAGE,
                "offset": offset,
            })
            wallets = data.get("jetton_wallets")
            if not isinstance(wallets, list):
                raise IndexerError("ION indexer returned no jetton wallet list")
            for wallet in wallets:
                if wallet.get("jetton") and wallet.get("owner"):
                    wallet_address = raw_address(wallet["address"])
                    if wallet_address in seen:
                        continue
                    seen.add(wallet_address)
                    found[(raw_address(wallet["jetton"]), raw_address(wallet["owner"]))] += int(wallet["balance"])
            if len(wallets) < PAGE:
                return found
            offset += len(wallets)

    async def _native_balances(self, owners: list[str]) -> dict[str, int]:
        data = await self._indexer("/accountStates", {"address": owners})
        accounts = data.get("accounts")
        if not isinstance(accounts, list):
            raise IndexerError("ION indexer returned no account state list")
        balances = {raw_address(item["address"]): int(item["balance"]) for item in accounts}
        if set(owners) - balances.keys():
            raise IndexerError("ION indexer omitted requested account states")
        return balances

    async def _lion_rate(self) -> Decimal:
        data = await self._request("GET", f"{self.staking_api_url}/staking/common")
        try:
            rate = Decimal(str(data["liquid"]["currentRate"]))
        except (KeyError, TypeError, InvalidOperation) as error:
            raise IndexerError("ION backend returned no LION staking rate") from error
        if not rate.is_finite() or rate <= 0:
            raise IndexerError("ION backend returned an invalid LION staking rate")
        return rate

    async def balances(self, tokens: Sequence[TokenData], owners: Sequence[str]) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {token.address: {} for token in tokens}
        unique_owners = list(dict.fromkeys(raw_address(owner) for owner in owners))
        native = next((token for token in tokens if token.type == TokenType.NATIVE), None)
        jettons = [token for token in tokens if token.type == TokenType.JETTON]
        masters = list(dict.fromkeys([*(raw_address(token.address) for token in jettons), *([self.lion_jetton] if native else [])]))
        all_jetton_balances: Counter[tuple[str, str]] = Counter()

        for batch in batched(unique_owners, OWNERS_PER_REQUEST):
            owner_batch = list(batch)
            if native:
                result[native.address].update(await self._native_balances(owner_batch))
            if masters:
                all_jetton_balances += await self._jetton_balances(masters, owner_batch)

        if native:
            lion_balances = {owner: all_jetton_balances[(self.lion_jetton, owner)] for owner in unique_owners}
            if any(lion_balances.values()):
                rate = await self._lion_rate()
                for owner in unique_owners:
                    result[native.address][owner] = ion_equivalent(
                        result[native.address][owner], lion_balances[owner], NATIVE_DECIMALS, rate
                    )

        for token in jettons:
            master = raw_address(token.address)
            result[token.address] = {
                owner: all_jetton_balances[(master, owner)]
                for owner in unique_owners
                if all_jetton_balances[(master, owner)]
            }
        return result

    async def has_holders(self, token: TokenData) -> bool:
        if token.type == TokenType.NATIVE:
            return True
        data = await self._indexer("/jetton/wallets", {
            "jetton_address": token.address,
            "exclude_zero_balance": "true",
            "limit": 1,
        })
        wallets = data.get("jetton_wallets")
        if not isinstance(wallets, list):
            raise IndexerError("ION indexer returned no jetton wallet list")
        return bool(wallets)

    async def public_key(self, address: Address) -> PublicKey | None:
        data = await self._request("POST", f"{self.url}/http/v2/jsonRPC", json={
            "id": 1,
            "jsonrpc": "2.0",
            "method": "runGetMethod",
            "params": {"address": address.to_str(is_user_friendly=False), "method": "get_public_key", "stack": []},
        })
        result = data.get("result") or {}
        if result.get("exit_code") != 0 or not result.get("stack"):
            return None
        value = result["stack"][0][1]
        return PublicKey(int(value, 0).to_bytes(32, "big"))
