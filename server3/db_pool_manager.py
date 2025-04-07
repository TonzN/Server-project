import asyncpg as pg

class PoolManager:
    """Manages multiple database connection pools.  """
    def __init__(self):
        self._pools = {}
    
    async def initialize(self, pool_name="main_pool"):
        pool = await setup_db_connectionpool()
        self.add_pool(pool_name, pool)

    def add_pool(self, name, pool):
        if name not in self._pools:
            self._pools[name] = pool
        else:
            raise RuntimeError("PoolManager->add_pool->Pool already exists")

    def get_pool(self, name, ignore=True):
        if name in self._pools:
            return self._pools[name]
        elif ignore == False:
            raise RuntimeError("Pool not found")
        else:
            return None
        
async def setup_db_connectionpool():
    """Set up a connection pool to the database.  """
    try:
        pool = await pg.create_pool(
            host="database.cf0yoiaesmqc.eu-north-1.rds.amazonaws.com",
            port="5432",
            user="postgres",
            password="toniNyt05#2030",
            min_size = 1,   
            max_size = 10
        )
        return pool
        
    except Exception as e:
        print(f"setup_db_connectionpool->Database connection pool error: {e}")
        return None

def get_connection(_db_pool):
    """
    Get a connection from the database pool."""
    try:
        if _db_pool is None:
            raise RuntimeError("DB pool not initialized")
        return _db_pool.acquire()
    except Exception as e:
        print(f"Error acquiring connection: {e}")   

def release_connection(_db_pool, conn):
    """Release a connection back to the database pool."""
    try:
        if _db_pool:
            _db_pool.release(conn)
    except Exception as e:  
        print(f"Error releasing connection: {e}")

def close_all_connections(_db_pool):
    """Close all connections in the database pool."""
    try:
        if _db_pool:
            _db_pool.close()
    except Exception as e:
        print(f"Error closing all connections: {e}")    

async def test_db():
    print("\nTesting database connection...")
    try:
        conn = await pg.connect(
            host="database.cf0yoiaesmqc.eu-north-1.rds.amazonaws.com",
            port="5432",
            user="postgres",
            password="toniNyt05#2030",
        )
    except Exception as e:
        print(f"test_db->Error connecting to database: {e}")
        return
    
    print(f"\tTest conneection: {conn} ")
    # Show all table names in the public schema
    try:
        rows = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
    except Exception as e:
        print("Unable to get tables from database")
        print(f"test_db->Error fetching table names: {e}")
        return 

    print("\n Getting tables... \nTables:\n")
    for row in rows:
        print("-", row['table_name'])

    await conn.close()

    return True
