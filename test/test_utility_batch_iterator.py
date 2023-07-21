import pytest
from utility import batch_iterator

def test_batch_iterator__with_numberListSize15_4batchSize():
    numbers : list[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    iterator = batch_iterator(numbers, 4)
    assert next(iterator) == [1, 2, 3, 4]
    assert next(iterator) == [5, 6, 7, 8]
    assert next(iterator) == [9, 10, 11, 12]
    assert next(iterator) == [13, 14, 15]
    with pytest.raises(StopIteration):
        next(iterator)

def test_batch_iterator__with_numberListSize4_1batchSize():
    numbers : list[int] = [1, 2, 3, 4]
    iterator = batch_iterator(numbers, 1)
    assert next(iterator) == [1]
    assert next(iterator) == [2]
    assert next(iterator) == [3]
    assert next(iterator) == [4]
    with pytest.raises(StopIteration):
        next(iterator)

def test_batch_iterator__with_numberListSize5_lessThan1batchSize():
    numbers : list[int] = [1, 2, 3, 4, 5]
    with pytest.raises(ValueError):
        iterator = batch_iterator(numbers, -5)
    with pytest.raises(ValueError):
        iterator = batch_iterator(numbers, 0)


def test_batch_iterator__with_numberListSize0_5batchSize():
    numbers : list[int] = []  
    iterator = batch_iterator(numbers, 5)
    with pytest.raises(StopIteration):
        next(iterator)


def test_batch_iterator__with_numberList_largerThanSizebatchSize():
    numbers : list[int] = [1, 2, 3, 4, 5]   
    iterator = batch_iterator(numbers, 10)
    assert next(iterator) == numbers


def test_batch_iterator__with_mixedList_3batchSize():
    numbers : list = [1, "sus", [1, 2, 3], True, 5]   
    iterator = batch_iterator(numbers, 3)
    assert next(iterator) == [1, "sus", [1, 2, 3]]
    assert next(iterator) == [True, 5]
    with pytest.raises(StopIteration):
        next(iterator)