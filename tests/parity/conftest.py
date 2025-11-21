import shutil
import tempfile
from pathlib import Path

import pytest

from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.sqlite_storage import SQLiteStorage


@pytest.fixture
def jsonl_storage():
    temp_dir = tempfile.mkdtemp()
    storage = JSONLStorage(storage_path=Path(temp_dir))
    storage.connect()
    yield storage
    storage.close()
    shutil.rmtree(temp_dir)


@pytest.fixture
def sqlite_storage():
    temp_dir = tempfile.mkdtemp()
    storage = SQLiteStorage(storage_path=Path(temp_dir))
    storage.connect()
    yield storage
    storage.close()
    shutil.rmtree(temp_dir)


@pytest.fixture(params=["jsonl", "sqlite"])
def storage(request, jsonl_storage, sqlite_storage):
    if request.param == "jsonl":
        return jsonl_storage
    else:
        return sqlite_storage
