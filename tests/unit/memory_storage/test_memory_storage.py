import os

import pytest

from apify.memory_storage.memory_storage import MemoryStorage


async def test_write_metadata(tmp_path: str) -> None:
    dataset_name = 'test'
    dataset_no_metadata_name = 'test-no-metadata'
    ms = MemoryStorage(local_data_directory=tmp_path, write_metadata=True)
    ms_no_metadata = MemoryStorage(local_data_directory=tmp_path, write_metadata=False)
    datasets_client = ms.datasets()
    datasets_no_metadata_client = ms_no_metadata.datasets()
    await datasets_client.get_or_create(name=dataset_name)
    await datasets_no_metadata_client.get_or_create(name=dataset_no_metadata_name)
    assert os.path.exists(os.path.join(ms._datasets_directory, dataset_name, '__metadata__.json')) is True
    assert os.path.exists(os.path.join(ms_no_metadata._datasets_directory, dataset_no_metadata_name, '__metadata__.json')) is False


async def test_persist_storage(tmp_path: str) -> None:
    ms = MemoryStorage(local_data_directory=tmp_path, persist_storage=True)
    ms_no_persist = MemoryStorage(local_data_directory=tmp_path, persist_storage=False)
    kvs_client = ms.key_value_stores()
    kvs_no_metadata_client = ms_no_persist.key_value_stores()
    kvs_info = await kvs_client.get_or_create(name='kvs')
    kvs_no_metadata_info = await kvs_no_metadata_client.get_or_create(name='kvs-no-persist')
    await ms.key_value_store(kvs_info['id']).set_record('test', {'x': 1}, 'application/json')
    await ms_no_persist.key_value_store(kvs_no_metadata_info['id']).set_record('test', {'x': 1}, 'application/json')
    assert os.path.exists(os.path.join(ms._key_value_stores_directory, kvs_info['name'], 'test.json')) is True
    assert os.path.exists(os.path.join(ms_no_persist._key_value_stores_directory, kvs_no_metadata_info['name'], 'test.json')) is False


def test_config_via_env_vars_persist_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: str) -> None:
    # Env var changes persist_storage to False
    monkeypatch.setenv('APIFY_PERSIST_STORAGE', 'false')
    ms = MemoryStorage(local_data_directory=tmp_path)
    assert ms._persist_storage is False
    monkeypatch.setenv('APIFY_PERSIST_STORAGE', '0')
    ms = MemoryStorage(local_data_directory=tmp_path)
    assert ms._persist_storage is False
    monkeypatch.setenv('APIFY_PERSIST_STORAGE', '')
    ms = MemoryStorage(local_data_directory=tmp_path)
    assert ms._persist_storage is False
    # Test if constructor arg takes precedence over env var value
    ms = MemoryStorage(local_data_directory=tmp_path, persist_storage=True)
    assert ms._persist_storage is True


def test_config_via_env_vars_write_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: str) -> None:
    # Env var changes write_metadata to True
    monkeypatch.setenv('DEBUG', '*')
    ms = MemoryStorage(local_data_directory=tmp_path)
    assert ms._write_metadata is True
    # Test if constructor arg takes precedence over env var value
    ms = MemoryStorage(local_data_directory=tmp_path, write_metadata=False)
    assert ms._write_metadata is False


async def test_purge_datasets(tmp_path: str) -> None:
    ms = MemoryStorage(local_data_directory=tmp_path, write_metadata=True)
    # Create default and non-default datasets
    datasets_client = ms.datasets()
    default_dataset_info = await datasets_client.get_or_create(name='default')
    non_default_dataset_info = await datasets_client.get_or_create(name='non-default')

    # Check all folders inside datasets directory before and after purge
    folders_before_purge = os.listdir(ms._datasets_directory)
    assert default_dataset_info['name'] in folders_before_purge
    assert non_default_dataset_info['name'] in folders_before_purge
    await ms.purge()
    folders_after_purge = os.listdir(ms._datasets_directory)
    assert default_dataset_info['name'] not in folders_after_purge
    assert non_default_dataset_info['name'] in folders_after_purge


async def test_purge_key_value_stores(tmp_path: str) -> None:
    ms = MemoryStorage(local_data_directory=tmp_path, write_metadata=True)

    # Create default and non-default key-value stores
    kvs_client = ms.key_value_stores()
    default_kvs_info = await kvs_client.get_or_create(name='default')
    non_default_kvs_info = await kvs_client.get_or_create(name='non-default')
    default_kvs_client = ms.key_value_store(default_kvs_info['id'])
    # INPUT.json should be kept
    await default_kvs_client.set_record('INPUT', {'abc': 123}, 'application/json')
    # test.json should not be kept
    await default_kvs_client.set_record('test', {'abc': 123}, 'application/json')

    # Check all folders and files inside kvs directory before and after purge
    folders_before_purge = os.listdir(ms._key_value_stores_directory)
    assert default_kvs_info['name'] in folders_before_purge
    assert non_default_kvs_info['name'] in folders_before_purge
    default_folder_files_before_purge = os.listdir(os.path.join(ms._key_value_stores_directory, 'default'))
    assert 'INPUT.json' in default_folder_files_before_purge
    assert 'test.json' in default_folder_files_before_purge
    await ms.purge()
    folders_after_purge = os.listdir(ms._key_value_stores_directory)
    assert default_kvs_info['name'] in folders_after_purge
    assert non_default_kvs_info['name'] in folders_after_purge
    default_folder_files_after_purge = os.listdir(os.path.join(ms._key_value_stores_directory, 'default'))
    assert 'INPUT.json' in default_folder_files_after_purge
    assert 'test.json' not in default_folder_files_after_purge


async def test_purge_request_queues(tmp_path: str) -> None:
    ms = MemoryStorage(local_data_directory=tmp_path, write_metadata=True)
    # Create default and non-default request queues
    rq_client = ms.request_queues()
    default_rq_info = await rq_client.get_or_create(name='default')
    non_default_rq_info = await rq_client.get_or_create(name='non-default')

    # Check all folders inside rq directory before and after purge
    folders_before_purge = os.listdir(ms._request_queues_directory)
    assert default_rq_info['name'] in folders_before_purge
    assert non_default_rq_info['name'] in folders_before_purge
    await ms.purge()
    folders_after_purge = os.listdir(ms._request_queues_directory)
    assert default_rq_info['name'] not in folders_after_purge
    assert non_default_rq_info['name'] in folders_after_purge