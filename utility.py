import math
from typing import TypeVar, Generic, Optional, Callable, Any



class batch_iterator:
    def __init__(self, array : list, batchSize : int):
        # Check batch size
        if batchSize <= 0:
            raise ValueError("Step size cannot be less than 1")
        # Variables
        self.array = array
        self.batchSize = batchSize
        self.totalBatches = math.ceil(len(array) / batchSize)
        self.currentBatch = 0

    def __iter__(self):
        return self

    def __next__(self):
        if (self.currentBatch >= self.totalBatches):
            raise StopIteration
        batch : list = self.array[self.batchSize*self.currentBatch:self.batchSize*(self.currentBatch+1)]
        self.currentBatch += 1
        return batch



class multi_batch_iterator:
    def __init__(self, array : list[list], batchSize : int):
        # Check batch size
        if batchSize <= 0:
            raise ValueError("Step size cannot be less than 1")
        # Check fields are equal size
        fieldSize = 0
        if len(array): fieldSize = len(array[0])

        size : int = fieldSize
        for i, field in enumerate(array):
            if (size != len(field)):
                str_array1 : str = str(array[0])
                str_array2 : str = str(field)
                if fieldSize > 5: 
                    str_array1 = str(array[0][:5])[:-1] + ", ...]"
                if len(field) > 5: 
                    str_array2 = str(field[:5])[:-1] + ", ...]"
                raise ValueError(f"All fields must be the same size:\nIndex {0} - len({str_array1}) == {fieldSize}\nIndex {i} - len({str_array2}) == {len(field)}")
        # Variables    
        self.array = array
        self.batchSize = batchSize
        self.totalBatches = math.ceil(fieldSize / batchSize)
        self.currentBatch = 0

    def __iter__(self):
        return self

    def __next__(self):
        if (self.currentBatch >= self.totalBatches):
            raise StopIteration
        batch : list[list] = [
            field[self.batchSize*self.currentBatch:self.batchSize*(self.currentBatch+1)] 
            for field in self.array
        ]
        self.currentBatch += 1
        return batch
    


T = TypeVar("T")
E = TypeVar("E")

class Result(Generic[T]):
    def __init__(self, value: Optional[T] = None, error: Optional[Exception] = None):
        self.value = value
        self.error = error


    def is_valid(self) -> bool:
        if   self.value is not None: return True
        elif self.error is not None: return False
        else:                        raise Exception("Result does not contains anything.")

    def unwrap(self) -> T:
        if   self.value is not None: return self.value
        elif self.error is not None: raise self.error
        else:                        raise Exception("Result does not contains anything.")

    def unwrap_or(self, default_value: T) -> T:
        return self.value if self.value is not None else default_value

    def expect(self, error_message: str) -> T:
        if self.value is not None:  return self.value
        else:                       raise Exception(error_message)

    def on_error(self, func: Callable[[Exception], Any]) -> 'Result[T]':
        if self.error is not None:
            func(self.error)
        return self
    
    def map(self, func: Callable[[T], E]) -> 'Result[E]':
        if   self.value is not None: return Result.ok(func(self.value))
        elif self.error is not None: return Result.err(self.error)
        else:                        raise Exception("Result does not contains anything.")

    @staticmethod
    def ok(value: T) -> 'Result[T]':
        return Result(value=value)

    @staticmethod
    def err(error: Exception) -> 'Result[E]':
        return Result(error=error)
