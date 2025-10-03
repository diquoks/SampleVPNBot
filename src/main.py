import asyncio
import client


async def main() -> None:
    bot = client.AiogramClient()
    await bot.polling_coroutine()


if __name__ == "__main__":
    asyncio.run(main())
