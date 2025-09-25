import tempfile
from pathlib import Path
from guignomap.backup import BackupManager
import sqlite3

def test_backup_manager_creates_backup():
    with tempfile.TemporaryDirectory() as tempdir:
        backup_dir = Path(tempdir) / "backup"
        db_path = Path(tempdir) / "test.db"
        # Crée une fausse DB
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        # Instancie le manager et crée le backup
        manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
        backup_file = manager.backup_db(tag="test")
        assert backup_file is not None
        assert backup_file.parent == backup_dir
        assert backup_file.exists()
