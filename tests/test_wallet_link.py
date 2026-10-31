import unittest
from urllib.parse import parse_qs, urlsplit

from app.bot.handlers.private.wallet.view import ion_wallet_link


class WalletLinkTests(unittest.TestCase):
    def test_generic_gateway_link_opens_ion_wallet_connect_page(self) -> None:
        link = ion_wallet_link(
            "tc://?v=2&id=client-id&r=request-data",
            "https://connect.ionwallet.io",
            "none",
        )

        parts = urlsplit(link)
        self.assertEqual(parts.scheme, "https")
        self.assertEqual(parts.netloc, "connect.ionwallet.io")
        self.assertEqual(
            parse_qs(parts.query),
            {
                "v": ["2"],
                "id": ["client-id"],
                "r": ["request-data"],
                "ret": ["none"],
            },
        )


if __name__ == "__main__":
    unittest.main()
