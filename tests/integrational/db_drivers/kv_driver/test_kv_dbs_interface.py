import pytest
from chromadb.errors import ChromaError

import sys
sys.path.insert(0, "../")

from cases import KVDB_POPULATED_CREATE_TEST_CASES, KVDB_POPULATED_DELETE_TEST_CASES, \
    KVDB_POPULATED_READ_TEST_CASES, KVDB_POPULATED_COUNT_TEST_CASES, KVDB_POPULATED_EXIST_TEST_CASES, \
    KVDB_POPULATED_CLEAR_TEST_CASES

@pytest.mark.parametrize("input, expected, keyvaluedb_conn", KVDB_POPULATED_CREATE_TEST_CASES, indirect=['keyvaluedb_conn'])
def test_create(input, expected, keyvaluedb_conn):
    keyvaluedb_conn.clear()

    try:
        for inp in input:
            keyvaluedb_conn.create(inp)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    assert keyvaluedb_conn.count_items() == expected['db_size']

@pytest.mark.parametrize("instances, input, expected, keyvaluedb_conn", KVDB_POPULATED_DELETE_TEST_CASES, indirect=['keyvaluedb_conn'])
def test_delete(instances, input, expected, keyvaluedb_conn):
    keyvaluedb_conn.clear()
    keyvaluedb_conn.create(instances)

    try:
        keyvaluedb_conn.delete(input)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    assert keyvaluedb_conn.count_items() == expected['db_size']


@pytest.mark.parametrize("instances, input, expected, keyvaluedb_conn", KVDB_POPULATED_READ_TEST_CASES, indirect=['keyvaluedb_conn'])
def test_read(instances, input, expected, keyvaluedb_conn):
    keyvaluedb_conn.clear()
    keyvaluedb_conn.create(instances)

    try:
        output = keyvaluedb_conn.read(input)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    if not expected['exception']:
        assert list(map(lambda item: None if item is None else item.id, output)) == expected['output_ids']


@pytest.mark.parametrize("instances, expected, keyvaluedb_conn", KVDB_POPULATED_COUNT_TEST_CASES, indirect=['keyvaluedb_conn'])
def test_count(instances, expected, keyvaluedb_conn):
    keyvaluedb_conn.clear()
    keyvaluedb_conn.create(instances)

    assert keyvaluedb_conn.count_items() == expected


@pytest.mark.parametrize("instances, input, expected, keyvaluedb_conn", KVDB_POPULATED_EXIST_TEST_CASES, indirect=['keyvaluedb_conn'])
def test_exist(instances, input, expected, keyvaluedb_conn):
    keyvaluedb_conn.clear()
    keyvaluedb_conn.create(instances)

    try:
        real = keyvaluedb_conn.item_exist(input)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    if not expected['exception']:
        assert real == expected['exist']


@pytest.mark.parametrize("instances, keyvaluedb_conn", KVDB_POPULATED_CLEAR_TEST_CASES, indirect=['keyvaluedb_conn'])
def test_clear(instances, keyvaluedb_conn):
    keyvaluedb_conn.clear()
    keyvaluedb_conn.create(instances)

    assert keyvaluedb_conn.count_items() == len(instances)
    keyvaluedb_conn.clear()
    assert keyvaluedb_conn.count_items() == 0
