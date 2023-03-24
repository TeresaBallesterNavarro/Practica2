"""
PRACTICA 2.2 - Programacion Paralela
Teresa Ballester Navarro

En esta práctica vamos a decidir a quien darle el turno de entrada al puente. Quitamos las 
variables de acceso (de la versión 2.1 con peatones) y vamos a establecer un orden de acceso al puente.
Para indicar los turnos en este caso, creamos una variable compartida turn.
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value
from multiprocessing import Manager

SOUTH = 'SOUTH'
NORTH = 'NORTH'

NCARS = 6 #Numero de coches
NPED = 5 #Numero de peatones
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new peaton enters each 5s

class Monitor():
    
    def __init__(self, manager):
        self.mutex = Lock()
        
        self.cochesN = Value('i', 0) #Numero de coches cruzando el puente en direccion Norte
        self.cochesS = Value('i', 0) #Numero de coches cruzando el puente en direccion Sur
        self.peatones = Value('i', 0) #Numero de peatones cruzando el puente en cualquier direccion 

        self.pasoCoches_N = Condition(self.mutex) #Variable condicion para que un coche cruce hacia el norte
        self.pasoCoches_S = Condition(self.mutex) #Variable condicion para que un coche cruce hacia el sur
        self.pasoPeatones = Condition(self.mutex) #Variable condicion para que un peaton cruce
        
        self.waiting_CN = Value('i', 0) #Numero de coches esprando a cruzar el puente en direccion Norte
        self.waiting_CS = Value('i', 0) #Numero de coches esperando a cruzar el puente en direccion Sur
        self.waiting_P = Value('i', 0) #Numero de peatones esperando a cruzar el puente
        
        self.turn = Value('i', 0) #Variable que indica de quien es el turno de pasar:
        # 0 -> No hay nadie en el puente
        # 1 -> Coches hacia el  norte cruzando el puente
        # 2-> Coches hacia el sur cruzando el puente
        # 3 -> Peatones cruazando el puente

    def puede_pasar_cocheN(self):
        #Si no hay coches hacia el sur cruzando ni peatones y es su turno
        condicion = (self.cochesS.value == 0 and self.peatones.value == 0) and (self.turn.value == 1)\
            or self.turn.value == 0
        return condicion
    
    def puede_pasar_cocheS(self):
        #Si no hay coches hacia el norte cruzando ni peatones y es su turno
        condicion = (self.cochesN.value == 0 and self.peatones.value == 0) and (self.turn.value == 2)\
            or self.turn.value == 0
        return condicion
        
    def quiereEntrar_coche(self, direction):
        self.mutex.acquire()
        #self.establecer_direction(direction)
        #self.pasoCoches.wait_for(self.puede_pasar_coche)
        if (direction == NORTH):
            self.waiting_CN.value += 1
            self.pasoCoches_N.wait_for(self.puede_pasar_cocheN)
            self.waiting_CN.value -= 1
            self.cochesN.value += 1 
            self.turn.value = 1 #Hay un coche hacia el norte cruzando el puente
            
        if (direction == SOUTH):
            self.waiting_CS.value += 1
            self.pasoCoches_S.wait_for(self.puede_pasar_cocheS)
            self.waiting_CS.value -= 1
            self.cochesS.value += 1
            self.turn.value = 2 #Hay un coche hacie el sur cruzando el puente
            
        self.mutex.release()

    def salida_coche(self, direction):
        self.mutex.acquire()
        
        if (direction == NORTH):
            self.cochesN.value -= 1
            #Damos preferencia a entrar en el puente a aquellos que haya un mayor numero esperando
            if self.waiting_CS.value != 0:
                self.turn.value = 2 #Se le da paso a los coches en direccion sur
            elif self.waiting_P.value != 0 :
                self.turn.value = 3 #Se le da paso a los peatones
            else:
                self.turn.value = 0
                
            if self.cochesN.value == 0:
                self.pasoCoches_S.notify_all()
                self.pasoPeatones.notify_all()

        if (direction == SOUTH):
            self.cochesS.value -= 1
            if self.waiting_CN.value != 0 :
                self.turn.value = 1 #Se le da paso a los coches en direccion norte
            elif self.waiting_P.value != 0 :
                self.turn.value = 3 #Se le da paso a los peatones
            else:
                self.turn.value = 0
                
            if self.cochesS.value == 0:
                self.pasoCoches_N.notify_all()
                self.pasoPeatones.notify_all()
    
        self.mutex.release()
        
    def puede_pasar_peaton(self):
        #Si no hay coches cruzando el puente y es su turno
        condicion = (self.cochesS.value == 0 and self.cochesN.value == 0) and (self.turn.value == 3)\
            or self.turn.value == 0
       
        return condicion
    
    def quiereEntrar_peaton(self):
        self.mutex.acquire()
        self.waiting_P.value += 1
        self.pasoPeatones.wait_for(self.puede_pasar_peaton)
        self.waiting_P.value -= 1
        self.peatones.value += 1
        self.turn.value = 3 #Hay un peaton cruzando el puente
        self.mutex.release()

    def salida_peaton(self):
        self.mutex.acquire()
        self.peatones.value -= 1
        
        if self.waiting_CS.value != 0 : #and ((self.waiting_CS >= self.waiting_CN.value and self.waiting_CN >= self.waiting_P.value)\
            #or (self.waiting_CS>= self.waiting_P.value and self.waiting_P >= self.waiting_CN)):
            self.turn.value = 2 #Se le da paso a los coches en direccion sur
        elif self.waiting_CN.value != 0 : #and ((self.waiting_CN >= self.waiting_CS.value and self.waiting_CS >= self.waiting_P.value)\
            #or (self.waiting_CN>= self.waiting_P.value and self.waiting_P >= self.waiting_CS)):
            self.turn.value = 1 #Se le da paso a los coches en direccion norte
        else:
            self.turn.value = 0

        if self.peatones.value == 0:
            self.pasoCoches_N.notify_all()
            self.pasoCoches_S.notify_all()
            
        self.mutex.release()
    
    def __repr__(self) -> str:
        return f'Monitor< Coches_Norte: {self.cochesN.value}, Coches_Norte_Waiting : {self.waiting_CN.value},\
            Coches_Sur: {self.cochesS.value}, Coches_Sur_Waiting : {self.waiting_CS.value},\
                Peatones :  {self.peatones.value}, Peatones_Waiting : {self.waiting_P.value},> \n'
    
    
##################################################################################################################
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
