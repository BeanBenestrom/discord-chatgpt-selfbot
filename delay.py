from datetime import datetime, timedelta
from random import random
import math

from interface import DelayInterface



def naturalDelayFunc(
        number1_between_0_and_1     : float, 
        number2_between_0_and_1     : float, 
        minutes_since_previous_ping : float, 
        delay_after_1_hour          : float, 
        baseline_reaction_time      : float) -> float:
    '''Returns a quantity of time to wait in minutes'''
    # delay = h(rand) * ( q(rand)                 + 
    #                     f(since previous ping)  +
    #                     g(current_date)         ) + reaction time
    h = lambda x       : ( 2 * x + 1 )**3 * 0.5 + 1
    q = lambda x       : x ** 15
    f = lambda minutes : delay_after_1_hour * (2 - 2**(1 - (minutes / 60)))
    g = lambda         : 0
    #! All of these functions return time measured in minutes!
    
    return h(number1_between_0_and_1) * ( q(number2_between_0_and_1) + f(minutes_since_previous_ping) + g() ) + baseline_reaction_time



class NaturalDelay(DelayInterface):
    # delay = h(rand) * ( q(rand)                 + 
    #                     f(since previous ping)  +
    #                     g(current_date)         ) + reaction time
    previously_pinged_date: datetime
    delay_after_hour = 6                  # In minutes
    reaction_time = 0.2 / 60              # In minutes


    def __init__(self, randomness: bool=True) -> None:
        self.previously_pinged_date = datetime.now()
        self.randomness = randomness


    def ping(self) -> float:
        '''Returns a quantity of time to wait in minutes'''
        r = lambda : 0.5
        if self.randomness:
            r = lambda : random()

        current_date: datetime = datetime.now()
        delayInMinutes: float = naturalDelayFunc(
            r(), r(), 
            (current_date - self.previously_pinged_date).total_seconds() / 60, 
            self.delay_after_hour, 
            self.reaction_time
        )
        self.previously_pinged_date = current_date
        return delayInMinutes
    


class NoDelay(DelayInterface):
    def ping(self) -> float:
        return 0
    

if __name__ == "__main__":
    for i in [naturalDelayFunc(random(), random(), 10, 6, 0.2 / 60) for _ in range(10)]:
        min = math.floor(i*100)/100
        if min == 0: min = "0.00"
        print(f"Ping - {str(min)} min | {math.floor(i*60*100)/100} sec")