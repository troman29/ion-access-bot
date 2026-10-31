import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatMemberStatus

from app.bot.handlers.chats.router import member_joined


class GroupJoinTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_join_without_wallet_is_removed_and_tracked_until_removal_succeeds(self) -> None:
        event = SimpleNamespace(
            chat=SimpleNamespace(id=-123),
            new_chat_member=SimpleNamespace(user=SimpleNamespace(id=42), status=ChatMemberStatus.MEMBER),
        )
        bot = SimpleNamespace(id=7)
        storage = SimpleNamespace(
            get_chat=AsyncMock(return_value=object()),
            members=AsyncMock(return_value=set()),
            get_user=AsyncMock(return_value=None),
            add_member=AsyncMock(),
        )

        with patch("app.bot.handlers.chats.router.kick", new_callable=AsyncMock) as kick:
            await member_joined(event, bot, storage, SimpleNamespace())

        storage.add_member.assert_awaited_once_with(-123, 42)
        kick.assert_awaited_once_with(bot, storage, -123, 42)

    async def test_approved_join_is_not_checked_or_removed_again(self) -> None:
        event = SimpleNamespace(
            chat=SimpleNamespace(id=-123),
            new_chat_member=SimpleNamespace(user=SimpleNamespace(id=42), status=ChatMemberStatus.MEMBER),
        )
        bot = SimpleNamespace(id=7)
        storage = SimpleNamespace(
            get_chat=AsyncMock(return_value=object()),
            members=AsyncMock(return_value={42}),
            get_user=AsyncMock(),
            add_member=AsyncMock(),
        )

        with patch("app.bot.handlers.chats.router.kick", new_callable=AsyncMock) as kick:
            await member_joined(event, bot, storage, SimpleNamespace())

        storage.get_user.assert_not_awaited()
        storage.add_member.assert_not_awaited()
        kick.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
