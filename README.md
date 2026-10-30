# ION Token Gate

Telegram bot for private groups and channels. A user connects ION Wallet through ION Gateway and proves control of the wallet. The bot approves a join request only when the wallet meets every configured balance rule. It checks members again every `CHECK_INTERVAL` minutes and removes those who fall below a rule.

## Balance rules

- `ION` means native ION **plus** LION multiplied by `liquid.currentRate` from `GET https://api.ionwallet.io/staking/common`. Both holdings must be in the same wallet. The bot compares integer nano-ION amounts, rounding the staked contribution down.
- A jetton master address means the balance of that ION jetton alone. NFT rules are unavailable.
- Rules are configured in the bot's `/admin` menu. All rules apply to all registered chats, and a member must pass **every** rule. For the initial ION Whales group, add `ION` with a minimum of `5000`. The minimum can be edited later in `/admin`.
- If the ION indexer or staking rate is unavailable, a join request is not approved and an existing member is not removed on the basis of an unknown balance.

## Deploy with Dokploy

Deploy this repository's `compose.yaml` as a Compose application. The stack has a bot and a Redis service with a persistent named volume; it publishes no network ports. Set `BOT_TOKEN` and `BOT_ADMIN_ID` as Dokploy environment variables. See `.env.example` for the remaining optional variables. The bot uses Telegram polling.

The ION Gateway manifest at `https://ionwallet.io/access-manifest.json` must be published before the bot starts. The bot reads the ION wallet entry from `ice-blockchain/wallets-list` and has a local fallback in `assets/wallets.json`.

Create the bot with BotFather. Add it as an administrator to the private Telegram group with **invite users** and **ban users** permissions. Send `/start` to the bot, then use `/admin` to add the `ION` rule and confirm the group. Share only the join-request link created by the bot; revoke other invite links that bypass approval.

For local development, copy `.env.example` to `.env`, set `BOT_TOKEN` and `BOT_ADMIN_ID`, then run `docker compose up --build`.

## ION services

- Native balance and jetton balances: `https://api.mainnet.ice.io/indexer/v3`
- Wallet public key lookup: `https://api.mainnet.ice.io/http/v2/jsonRPC`
- LION exchange rate: `https://api.ionwallet.io/staking/common`
- Wallet bridge: `https://bridge.ionwallet.io/bridge/`

The original [TON Token Gate](https://github.com/nessshon/tontokengate-bot) is MIT licensed; its copyright notice remains in `LICENSE`.
