from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram.types import User
from aiogram_tonconnect import Texts, View
from aiogram_tonconnect.core.models import Operation
from aiogram_tonconnect.view.view import Screen
from ton_connect.models import AppWallet

from app.storage import Storage
from app.texts import SUPPORTED_LANGUAGES, TextButton, TextMessage


def wallet_texts(language_code: str) -> Texts:
    message, button = TextMessage(language_code), TextButton(language_code)
    failed = message.get("connect_wallet_failed")
    return Texts(
        connect=message.get("connect_wallet"),
        rejected=message.get("connect_wallet_rejected"),
        timeout=message.get("connect_wallet_timeout"),
        wrong_network=message.get("connect_wallet_wrong_network"),
        bad_signature=message.get("connect_wallet_proof_wrong"),
        bad_manifest=message.get("connect_wallet_bad_manifest"),
        not_supported=failed,
        not_connected=failed,
        unavailable=failed,
        failed=failed,
        open_wallet=button.get("connect_wallet"),
        go_back=button.get("back"),
        unknown_wallet=message.get("any_wallet"),
    )


class WalletView(View):
    def __init__(self, storage: Storage) -> None:
        super().__init__(texts={code: wallet_texts(code) for code in SUPPORTED_LANGUAGES})
        self.storage = storage

    async def language(self, user: User) -> str | None:
        user_data = await self.storage.get_user(user.id)
        if user_data is not None and user_data.language_code:
            return user_data.language_code
        return await super().language(user)

    async def connect(
        self,
        operation: Operation,
        wallets: list[AppWallet],
        selected: AppWallet | None,
        qr_link: str,
        open_link: str | None,
        page: int,
    ) -> Screen:
        if selected is None:
            selected = wallets[0]
            qr_link = ion_wallet_link(qr_link, selected.universal_url, "none")
            open_link = ion_wallet_link(qr_link, selected.universal_url, "back")
        return await super().connect(operation, wallets, selected, qr_link, open_link, page)


def ion_wallet_link(link: str, universal_url: str | None, return_strategy: str) -> str:
    if universal_url is None:
        raise ValueError("ION Wallet has no universal URL")
    source = urlsplit(link)
    target = urlsplit(universal_url)
    if source.scheme not in {"tc", "https"} or target.scheme != "https":
        raise ValueError("Invalid ION Gateway connect URL")
    params = dict(parse_qsl(source.query, keep_blank_values=True))
    params["ret"] = return_strategy
    return urlunsplit((target.scheme, target.netloc, target.path, urlencode(params), ""))
