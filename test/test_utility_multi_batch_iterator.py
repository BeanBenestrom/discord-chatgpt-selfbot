import pytest
from utility import multi_batch_iterator

def test_multi_batch_iterator__with_listSize5_3batchSize():
    array : list[list] = [
        [ 1,   2,   3,   4,   5 ], 
        ["a", "b", "c", "d", "e"]
    ]
    iterator = multi_batch_iterator(array, 3)
    assert next(iterator) == [[1, 2, 3], ["a", "b", "c"]]
    assert next(iterator) == [[4, 5], ["d", "e"]]
    with pytest.raises(StopIteration):
        next(iterator)

def test_multi_batch_iterator__with_listSize4_1batchSize():
    array : list[list] = [
        [ 1,   2,   3,   4,   5 ], 
        ["a", "b", "c", "d", "e"]
    ]
    iterator = multi_batch_iterator(array, 1)
    assert next(iterator) == [[1], ["a"]]
    assert next(iterator) == [[2], ["b"]]
    assert next(iterator) == [[3], ["c"]]
    assert next(iterator) == [[4], ["d"]]
    assert next(iterator) == [[5], ["e"]]
    with pytest.raises(StopIteration):
        next(iterator)

def test_multi_batch_iterator__with_listSize5_lessThan1batchSize():
    array : list[list] = [
        [ 1,   2,   3,   4,   5 ], 
        ["a", "b", "c", "d", "e"]
    ]
    with pytest.raises(ValueError):
        iterator = multi_batch_iterator(array, -5)
    with pytest.raises(ValueError):
        iterator = multi_batch_iterator(array, 0)


def test_multi_batch_iterator__with_listSize0_5batchSize():
    array : list[list] = []
    iterator = multi_batch_iterator(array, 5)
    with pytest.raises(StopIteration):
        next(iterator)


def test_multi_batch_iterator__with_list_largerThanListSizebatchSize():
    array : list[list] = [
        [ 1,   2,   3,   4,   5 ], 
        ["a", "b", "c", "d", "e"]
    ]  
    iterator = multi_batch_iterator(array, 10)
    assert next(iterator) == array


def test_multi_batch_iterator__with_mixedList_3batchSize():
    array : list[list] = [
        [ 1, "hi", True,   4,    5 ], 
        ["a", 42,   "c", False, True]
    ]  
    iterator = multi_batch_iterator(array, 3)
    assert next(iterator) == [[1, "hi", True], ["a", 42, "c"]]
    assert next(iterator) == [[4, 5], [False, True]]
    with pytest.raises(StopIteration):
        next(iterator)


def test_multi_batch_iterator__different_field_size():
    array : list[list] = [
        [ 1,   2,   3,   4,   5 ], 
        ["a", "b", "c", "d", "e", "f"]
    ] 
    with pytest.raises(ValueError):
        iterator = multi_batch_iterator(array, 10)