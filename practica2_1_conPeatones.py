"""
PRACTICA 2.1 con PEATONES - Programacion Paralela
Teresa Ballester Navarro

En esta práctica cosnideramos que solo puede haber coches en una misma direccion cruzando a la vez
el puente. Para ello, utilizaremos una variable compartida que nos indique si no hay nadie cruzando 
el puente (0), y lo contrario (1). La diferencia con la practica2_1, es que en esta también pueden
cruzar el puente peatones, en ambas direcciones. Pero no puede haber peatones y coches en ninguna
direccion cruzando el puente simultaneamente.
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value
from multiprocessing import Manager

SOUTH = 'SOUTH'
NORTH = 'NORTH'

NCARS = 60 #Numero de coches
NPED = 35 #Numero de peatones
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new peaton enters each 5s

class Monitor():
    
    def __init__(self, manager):
        self.mutex = Lock()
        
        self.cochesN = Value('i', 0) #Numero de coches cruzando el puente en direccion Norte
        self.cochesS = Value('i', 0) #Numero de coches cruzando el puente en direccion Sur
        self.peatones = Value('i', 0) #Numero de peatones cruzando el puente en cualquier direccion 
    
        self.d = NORTH
        self.acceso_coches = Value('i', 1)
        self.acceso_peatones = Value('i',0)
        self.pasoCoches= Condition(self.mutex)
        self.pasoPeatones = Condition(self.mutex)

    def establecer_direction(self, direction):
        self.d = direction
        
    def puede_pasar_coche(self):
        if (self.d == NORTH):
            noHayNadie = (self.cochesS.value == 0 and self.peatones.value == 0)
        else:
            noHayNadie = (self.cochesN.value == 0 and self.peatones.value == 0)
            
        return(self.acceso_coches.value or noHayNadie or self.acceso_peatones.value)
    
    def quiereEntrar_coche(self, direction):
        self.mutex.acquire()
        self.establecer_direction(direction)
        self.pasoCoches.wait_for(self.puede_pasar_coche)
        if (direction == NORTH):
            self.cochesN.value += 1
        else:
            self.cochesS.value += 1
        self.acceso_coches.value = 0 #Hay un coche cruzando el puente
        self.acceso_peatones.value = 0 
        self.mutex.release()

    def salida_coche(self, direction):
        self.mutex.acquire()
        if (direction == NORTH):
            self.cochesN.value -= 1
        else:
            self.cochesS.value -= 1
        if (self.cochesN.value == 0 and self.cochesS.value == 0 and self.peatones.value == 0):
            self.acceso_coches.value = 1 #No hay nadie cruzando el puente
            self.acceso_peatones.value = 1
        self.pasoCoches.notify_all()
        self.pasoPeatones.notify_all()
        self.mutex.release()
        
    def puede_pasar_peaton(self):
        noHayNadie = (self.cochesS.value == 0 and self.cochesN.value == 0)
       
        return(self.acceso_peatones.value or self.acceso_coches.value or noHayNadie)
    
    def quiereEntrar_peaton(self):
        self.mutex.acquire()
        self.pasoPeatones.wait_for(self.puede_pasar_peaton)
        self.peatones.value += 1
        self.acceso_peatones.value = 0 #Hay un coche cruzando el puente
        self.mutex.release()

    def salida_peaton(self):
        self.mutex.acquire()
        self.peatones.value -= 1
        if (self.cochesN.value == 0 and self.cochesS.value == 0 and self.peatones.value == 0):
            self.acceso_coches.value = 1 #No hay nadie cruzando el puente
            self.acceso_peatones.value = 1
        self.pasoPeatones.notify_all()
        self.pasoCoches.notify_all()
        self.mutex.release()
    
    def __repr__(self) -> str:
        return f'Monitor< Coches_Norte: {self.cochesN.value},\
            Coches_Sur: {self.cochesS.value}, Peatones :  {self.peatones.value}> \n'
    
    
#####################################################################################  
def delayCoche_Norte(factor = TIME_CARS_NORTH) -> None:
    time.sleep(factor)

def delayCoche_Sur(factor = TIME_CARS_SOUTH) -> None:
    time.sleep(factor)

def delayPeaton(factor = TIME_PED) -> None:
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
    
def peaton(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.quiereEntrar_peaton()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delayPeaton()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.salida_peaton()
    print(f"pedestrian {pid} out of the bridge. {monitor}")

def gen_peaton(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=peaton, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()
        
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
    gped = Process(target=gen_peaton, args=(monitor,))
    gcars_north.start()
    gcars_south.start()
    gped.start()
    gcars_north.join()
    gcars_south.join()
    gped.join()

if __name__ == '__main__':
    main()
