import threading, asyncio
import client


async def main() -> None:
    bot = client.AiogramClient()
    worker_thread = threading.Thread(
        target=asyncio.run,
        kwargs={
            "main": bot.worker(),
        },
        daemon=True,
        name="workerThread"
    )
    worker_thread.start()
    await bot.polling_coroutine()


if __name__ == "__main__":
    asyncio.run(main())
