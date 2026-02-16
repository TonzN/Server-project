import loads
from database_manager import *
import server_utils
import asyncio

loads.time.sleep(1)   

async def run_test():
         
    await server_pool.initialize()
    db_connection = await test_db()
    if not db_connection:
        print("Could not connect to database, closing server")
        return
    print("Connected to database")
    print("\n checking users table...\n")
    print("Found example usertables:")
    print(await db_get_user_profile("Toni"))
    print("\n\n")
    print(await db_get_user_profile("test"))
    print("\n\n")
    messages = await db_get_table("messages", limit=20, order_by="message_id", newest_first=True)
    for msg in messages:
        print("-" * 50)
        for key, value in msg.items():
            print(f"{key:<15}: {value}")

asyncio.run(run_test())
