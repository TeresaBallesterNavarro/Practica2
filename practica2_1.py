"""
PRACTICA 2.1 - Programacion Paralela
Teresa Ballester Navarro

En esta práctica cosnideramos que solo puede haber coches en una misma direccion cruzando a la vez
el puente. Para ello, utilizaremos una variable compartida que nos indique si no hay nadie cruzando 
el puente (0), y lo contrario (1).
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value
from multiprocessing import Manager

SOUTH = 'SOUTH'
NORTH = 'NORTH'

NCARS = 60 #Numero de coches
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s

class Monitor():
    
    def __init__(self, manager):
        self.mutex = Lock()
        
        self.cochesN = Value('i', 0) #Numero de coches cruzando el puente en direccion Norte
        self.cochesS = Value('i', 0) #Numero de coches cruzando el puente en direccion Sur
        
        self.d = NORTH
        self.acceso = Value('i', 1)
        self.puenteVacio= Condition(self.mutex)

    def establecer_direction(self, direction):
        self.d = direction
        
    def puede_pasar(self):
        if (self.d == NORTH):
            noHayNadie = (self.cochesS.value == 0)
        else:
            noHayNadie = (self.cochesN.value == 0)
        return(self.acceso.value or noHayNadie)
    
    def quiereEntrar_coche(self, direction):
        self.mutex.acquire()
        self.establecer_direction(direction)
        self.puenteVacio.wait_for(self.puede_pasar)
        if (direction == NORTH):
            self.cochesN.value += 1
        else:
            self.cochesS.value += 1
        self.acceso.value = 0 #Hay un coche cruzando el puente
        self.mutex.release()

    def salida_coche(self, direction):
        self.mutex.acquire()
        if (direction == NORTH):
            self.cochesN.value -= 1
        else:
            self.cochesS.value -= 1
        if (self.cochesN.value == 0 and self.cochesS.value == 0):
            self.acceso.value = 1 #No hay nadie cruzando el puente
        self.puenteVacio.notify_all()
        self.mutex.release()
    
    def __repr__(self) -> str:
        return f'Monitor< Coches_Norte: {self.cochesN.value}, Coches_Sur: {self.cochesS.value}>'

############################################################################################## 
def delayCoche_Norte(factor = TIME_CARS_NORTH) -> None:
    time.sleep(factor)

def delayCoche_Sur(factor = TIME_CARS_SOUTH) -> None:
    time.sleep(factor)

def coche(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.quiereEntrar_coche(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delayCoche_Norte()
    else:
        delayCoche_Sur()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.salida_coche(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def gen_coches(direction: int, time_cars, monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        cid += 1
        p = Process(target=coche, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/time_cars))

    for p in plst:
        p.join()

def main():
    manager = Manager()
    monitor = Monitor(manager)
    gcars_north = Process(target=gen_coches, args=(NORTH, TIME_CARS_NORTH, monitor))
    gcars_south = Process(target=gen_coches, args=(SOUTH, TIME_CARS_SOUTH, monitor))
    gcars_north.start()
    gcars_south.start()
    gcars_north.join()
    gcars_south.join() 
if __name__=='__main__':
    main()