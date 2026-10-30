import unittest
from collections import Counter
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.indexer.indexer import Indexer, IndexerError, ion_equivalent
from app.indexer.models import raw_address
from app.storage import TokenData, TokenType

OWNER = "UQA4ig8gg06oYwMPvgsLBbk0h00OhPiTAEMA4UdiiLBwt7nj"
LION = "EQACbwI38RnvclU5Wv6H9zDr8Ao_tq9NWilXxBmoE8yroZlF"


class IonBalanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.indexer = Indexer("https://api.mainnet.ice.io", "https://api.ionwallet.io", LION)
        self.owner = raw_address(OWNER)
        self.token = TokenData("ION", "ION including staked LION", TokenType.NATIVE, 5_000_000_000_000, "")

    async def test_staked_lion_counts_toward_native_ion_threshold(self) -> None:
        self.indexer._native_balances = AsyncMock(return_value={self.owner: 1_000_000_000_000})
        self.indexer._jetton_balances = AsyncMock(
            return_value=Counter({(raw_address(LION), self.owner): 3_000_000_000_000})
        )
        self.indexer._lion_rate = AsyncMock(return_value=Decimal("1.386104805"))

        balances = await self.indexer.balances([self.token], [OWNER])

        self.assertEqual(balances["ION"][self.owner], 5_158_314_415_000)
        self.assertGreaterEqual(balances["ION"][self.owner], self.token.min_amount)

    async def test_staking_rate_failure_cannot_turn_lion_into_zero(self) -> None:
        self.indexer._native_balances = AsyncMock(return_value={self.owner: 1_000_000_000_000})
        self.indexer._jetton_balances = AsyncMock(
            return_value=Counter({(raw_address(LION), self.owner): 3_000_000_000_000})
        )
        self.indexer._lion_rate = AsyncMock(side_effect=IndexerError("staking backend unavailable"))

        with self.assertRaises(IndexerError):
            await self.indexer.balances([self.token], [OWNER])

    async def test_no_lion_does_not_require_staking_rate(self) -> None:
        self.indexer._native_balances = AsyncMock(return_value={self.owner: 6_000_000_000_000})
        self.indexer._jetton_balances = AsyncMock(return_value=Counter())
        self.indexer._lion_rate = AsyncMock()

        balances = await self.indexer.balances([self.token], [OWNER])

        self.assertEqual(balances["ION"][self.owner], 6_000_000_000_000)
        self.indexer._lion_rate.assert_not_awaited()

    async def test_duplicate_wallet_on_next_page_is_not_counted_twice(self) -> None:
        wallet = {"address": OWNER, "owner": OWNER, "jetton": LION, "balance": "100"}
        second_wallet = {"address": LION, "owner": OWNER, "jetton": LION, "balance": "200"}
        self.indexer._indexer = AsyncMock(side_effect=[
            {"jetton_wallets": [wallet, second_wallet]},
            {"jetton_wallets": [wallet]},
        ])

        with patch("app.indexer.indexer.PAGE", 2):
            balances = await self.indexer._jetton_balances([raw_address(LION)], [self.owner])

        self.assertEqual(balances[(raw_address(LION), self.owner)], 300)
        self.assertEqual(self.indexer._indexer.await_count, 2)

    def test_fractional_nano_ion_is_rounded_down(self) -> None:
        self.assertEqual(ion_equivalent(0, 1, 9, Decimal("1.386104805")), 1)


if __name__ == "__main__":
    unittest.main()
