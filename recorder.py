from datetime import datetime, timedelta
import sqlite3
from homeassistant.core import HomeAssistant

DEFAULT_SNAPSHOT_PATH = "config/.storage/hyperbase-snapshot.db"
# DEFAULT_SNAPSHOT_PATH = ".storage/hyperbase-snapshot.db"

class FailedSnapshot:
    def __init__(self, id, start_time, end_time):
        self.failed_id = id
        self.start_time = start_time
        self.end_time = end_time


class SnapshotRecorder:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
    
    async def async_validate_table(self):
        await self.hass.async_add_executor_job(self.__create_table)
    
    def __create_table(self):
        db = sqlite3.connect(DEFAULT_SNAPSHOT_PATH)
        cur = db.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS snapshot(
            "id" INTEGER PRIMARY KEY,
            "timestamp" TEXT,
            connector_entity_id TEXT,
            payload TEXT,
            collection_id TEXT,
            project_id TEXT)
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS failed(
            "id" INTEGER PRIMARY KEY,
            start_snapshot_time TEXT,
            end_snapshot_time TEXT)
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS check_history(
            "id" INTEGER PRIMARY KEY,
            "timestamp" TEXT
            )""")
    
    
    def write_recorder(self, stored_data, project_id):
        data = [(
            message.get("timestamp"),
            message.get("connector_entity_id"),
            message.get("collection_id"),
            message.get("payload"),
            project_id) for message in stored_data]
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            cur.executemany("""
                INSERT INTO snapshot("timestamp", connector_entity_id, collection_id, payload, project_id)
                VALUES (?, ?, ?, ?, ?)
                """, data)
            db.commit()
    
    
    def write_fail_snapshot(self, start_time, end_time):
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            cur.execute("""
                INSERT INTO failed(start_snapshot_time, end_snapshot_time)
                VALUES (?, ?)
                """, (start_time, end_time))
            db.commit()
    
    
    def query_snapshots(self, start_time, end_time):
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            rows = cur.execute("""
                SELECT id, connector_entity_id, "timestamp" FROM snapshot
                WHERE "timestamp" >= ? AND "timestamp" < ?
                """, (start_time, end_time))
            data = rows.fetchall()
            data_set = [(item[1], item[2]) for item in data]
            data_mapping = {}
            for item in data:
                data_mapping[f"{item[1]}{item[2]}"] = item[0]
            return data_set, data_mapping
    
    
    def query_failed_snapshots(self):
        FAILED_ID = 0
        START_TIME = 1
        END_TIME = 2
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            rows = cur.execute("SELECT * FROM failed ORDER BY start_snapshot_time ASC")
            data = rows.fetchall()
            failed_snapshots = [FailedSnapshot(
                snapshot[FAILED_ID],
                snapshot[START_TIME],
                snapshot[END_TIME]) for snapshot in data]
            
            return failed_snapshots
    
    
    def flush_failed_snapshots(self, first_entry_start_time: str, last_entry_start_time: str):
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            cur.execute("DELETE FROM failed WHERE start_snapshot_time >= ? AND start_snapshot_time <= ?",
                (first_entry_start_time, last_entry_start_time))
            db.commit()
    
    
    def query_snapshots_by_ids(self, id_list: list):
        select_query = " or ".join(id_list)
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            rows = cur.execute(f"SELECT payload FROM snapshot WHERE {select_query}")
            payloads: list[str] = rows.fetchall()
            return payloads
    
    
    def delete_failed_snapshot_by_id(self, failed_id):
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            cur.execute("DELETE FROM failed WHERE id = ?",
                (failed_id, ))
            db.commit()
    
    
    def delete_old_snapshots(self):
        old_timestamp = datetime.now() - timedelta(days=7)
        
        with sqlite3.connect(DEFAULT_SNAPSHOT_PATH) as db:
            cur = db.cursor()
            cur.execute("DELETE FROM snapshot WHERE timestamp <= ?",
                (old_timestamp.isoformat(), ))
            db.commit()