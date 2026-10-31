from dataclasses import dataclass

from environs import Env, validate

from app.texts import SUPPORTED_LANGUAGES


@dataclass
class BotConfig:
    TOKEN: str
    ADMIN_ID: int
    GROUP_LANGUAGE: str


@dataclass
class RedisConfig:
    HOST: str
    PORT: int
    DB: int
    USERNAME: str | None
    PASSWORD: str | None


@dataclass
class IndexerConfig:
    URL: str
    STAKING_API_URL: str
    LION_JETTON: str
    KEY: str | None


@dataclass
class Config:
    bot: BotConfig
    redis: RedisConfig
    indexer: IndexerConfig

    MANIFEST_URL: str
    WALLETS_LIST_URL: str
    WALLETS: list[str]
    CHECK_INTERVAL: int


def load_config() -> Config:
    env = Env()
    env.read_env()

    return Config(
        bot=BotConfig(
            TOKEN=env.str("BOT_TOKEN"),
            ADMIN_ID=env.int("BOT_ADMIN_ID"),
            GROUP_LANGUAGE=env.str("BOT_GROUP_LANGUAGE", "ru", validate=validate.OneOf(SUPPORTED_LANGUAGES)),
        ),
        redis=RedisConfig(
            HOST=env.str("REDIS_HOST"),
            PORT=env.int("REDIS_PORT"),
            DB=env.int("REDIS_DB"),
            USERNAME=env.str("REDIS_USERNAME", None) or None,
            PASSWORD=env.str("REDIS_PASSWORD", None) or None,
        ),
        indexer=IndexerConfig(
            URL=env.str("ION_INDEXER_URL", "https://api.mainnet.ice.io"),
            STAKING_API_URL=env.str("ION_STAKING_API_URL", "https://api.ionwallet.io"),
            LION_JETTON=env.str("LION_JETTON", "EQACbwI38RnvclU5Wv6H9zDr8Ao_tq9NWilXxBmoE8yroZlF"),
            KEY=env.str("ION_INDEXER_KEY", None) or None,
        ),
        MANIFEST_URL=env.str("MANIFEST_URL"),
        WALLETS_LIST_URL=env.str(
            "WALLETS_LIST_URL",
            "https://raw.githubusercontent.com/ice-blockchain/wallets-list/refs/heads/master/wallets-v2.json",
        ),
        WALLETS=[name.strip() for name in env.list("WALLETS", ["ionwallet"], subcast=str)],
        CHECK_INTERVAL=env.int("CHECK_INTERVAL", 5, validate=validate.Range(min=1)),
    )
