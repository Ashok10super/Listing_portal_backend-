import asyncio
import os
import asyncpg
import bcrypt
from dotenv import load_dotenv

load_dotenv()

async def seed():
    conn = await asyncpg.connect(os.getenv("POSTGRES_URL"))
    
    salt = bcrypt.gensalt()
    pw_hash = bcrypt.hashpw(b"password123", salt).decode("utf-8")
    
    test_users = [
        ("superadmin@arx.com", "Super Admin", "9820012345", 1), # SUPER_ADMIN
        ("admin@arx.com", "Admin User", "9811054321", 2),      # ADMIN
        ("user@arx.com", "Buyer User", "9930088776", 4),       # USER
    ]
    
    for email, username, phone, role_id in test_users:
        existing = await conn.fetchrow('SELECT user_id, auth_id FROM "user" WHERE email = $1', email)
        if existing:
            print(f"{email} exists, updating password...")
            await conn.execute("UPDATE auth SET hash_password = $1 WHERE auth_id = $2", pw_hash, existing["auth_id"])
        else:
            print(f"Creating {email}...")
            auth_id = await conn.fetchval(
                "INSERT INTO auth (hash_password, is_user_active) VALUES ($1, true) RETURNING auth_id",
                pw_hash
            )
            await conn.execute(
                """
                INSERT INTO "user" (user_name, email, phone, role_id, auth_id, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                username, email, phone, role_id, auth_id
            )
            print(f"Created {email} with auth_id={auth_id}, role_id={role_id}")
            
    print("Done seeding users.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
