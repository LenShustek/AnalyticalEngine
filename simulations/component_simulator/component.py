'''file: component.py
    
    ******  A COMPONENT-LEVEL SIMULATOR FOR THE ANALYTICAL ENGINE  *******

This simulates the engine at a resolution of basic "time units", 15 or 20 of which comprise a "cycle".
The activities during a cycle are controlled by the current "verticals" on the microprogram barrels.

The model is of an interconnected assembly of hierarchical "components" that have internal state. 
Examples of components are:
   - digit wheels
   - stacks of digit wheels
   - axles that go through one or more interleaved stacks of digit wheels
   - anticipating carriage for an axle
   - barrels

Some components, like digit wheels, are eligible to change state sometime during a time unit, and they have an 
"advance" function that is called to do that. Other components are only conduits for state changes between other
components. For example, a "stack of digit wheels" is the conduit to transmit a state change in the axle it is on 
to all the wheels in the stack, some of which will then having pending state changes of their own.

We use the following process to try to emulate the parallelism in the engine:

1. Start by putting onto an "awaiting_advance" list the components that are eligible to be driven in some way
   by the Prime Mover.

2. Continually remove a random one of those components from the list and call its "advance" function so that
   it changes internal state based on its current state, as appropriate for a duration of one time unit.

3. When a component's current state changes, it is eligible to also create pending state changes in other components
   to which it is currently connected, perhaps indirectly throught a conduit. It then adds those components to the 
   "awaiting_advance" list so that those state changes will occur at a random time during the current time unit. 
   Here are some examples:
   - a turning digit wheel is meshed to another wheel, and so directly causes it to turn
   - a rotating axle has a finger that may be in position to impinge (using a stack of digit wheels as a conduit) 
     on the finger of one if its wheels, and so turns it

4. When the "awaiting_advance" list finally becomes empty, all the actions for this time unit are over.
   Increment to the next time unit and go to step 1.

The purpose of the randomization in step 2 is to reveal if there are any race conditions that depend on the 
order in which component state changes are done. It's not a proof, but making many runs with different 
orderings should help flush out problems. 

'''
import random
import traceback
from barrel_assembler import program, jumpstud

NDIGITS=30   # of digits in each number of a column, not including the sign
NPERCAGE=2   # of digits in a cage, ie how many numbers a column holds

TRACE_ADVANCE, TRACE_WHEELS, TRACE_BARRELS, TRACE_MESHES, TRACE_JUMPS = 1,2,4,8,16  #flags for which tracing output we want
TRACE_ALL = -1 

class Component: #every part that might be acted upon is a Component
   def __init__(self, typename:str, name:str):
      self.typename = typename
      self.name = name
      self.driven = False #are we being driven by something?

def error(thing, msg:str):
   print("ERROR: ", end="")
   if isinstance(thing, Component): print(f"{thing.typename} {thing.name} ", end="")
   if isinstance(thing, str): print(thing, end="")
   print(msg, "at timeunit", timeunit)
   traceback.print_stack()
   exit()

#define the various kinds of child components
#component class functions starting with "_" are simulator meta-functions, not engine actions
      
class DigitWheel(Component): #a basic digit wheel
# it can be moved conditionally by a finger on its axle that impinges on the finger of the wheel,
# or unconditionally because it is meshed with a wheel on another axis that has moved
# or unconditionally because the Anticipating Carriage is handing us a carry
   def __init__(self, typename, digitstack, digitnum):
       Component.__init__(self, typename, digitstack.name+".W"+str(digitnum))
       self.digitstack = digitstack
       self.digitnum = digitnum # 0 (least significant) to 31 (sign)
       self.position = 0 #current index position: 0 to 9
       self.nextposition = None
   def queue_movewheel(self, position): #queue us to have a wheel movement to "position"
      if trace & TRACE_WHEELS: print(f'         queuing move of {self.typename} {self.name} from {self.position} to {position}')
      if (position+1)%10 != self.position and (position-1)%10 != self.position:
         error(self, "is attempting to move more than one position")
      self.nextposition = position;
      add_to_advance_list(self) #add ourselves to the list of pending advances during this time unit
      for axlemesh in self.digitstack.meshed_axles: #schedule moves of the corresponding wheels of all the axles we are meshed to
         '''Each member of the meshed_axles list is itself a list of four elements: 
               [0] axle (an Axle): the axle that the wheel we are meshed to is on
               [1] cagewheel (an integer): the 0-origin number indicating which the wheel in the cage we are meshed to
               [2] stepcage (an integer): 0, +1, or -1 to indicate the cage relative to ours; this effects shifts
               [3] subtraction (a boolean): whether the meshed wheel should move in reverse to cause subtraction   '''
         targetdigit = self.digitnum+axlemesh[2]
         if targetdigit >= 0 and targetdigit < NDIGITS: #ignore shifts off either end
             #Question: if we are being subtracted from and the meshed axle is reversed, should we add to it? No use cases yet.
            axlemesh[0].digitstacks[axlemesh[1]].wheels[targetdigit].movewheel(axlemesh[3])
   def checkfinger(self, fingerpos): #our axle's finger just moved
      if (fingerpos + 1) % 10 == self.position: #it had been at our position
         self.queue_movewheel(fingerpos) #so we will schedule a move to where the axle finger is now
         return True
      else: return False #this wheel doesn't (yet) move
   def movewheel(self, subtraction:bool): #schedule one of the unconditional moves: meshed to, or carried to
      self.queue_movewheel((self.position + (-1 if subtraction else +1)) % 10)  #either same or opposite direction
   def advance(self): #manifest a queued change in position
         if self.nextposition is None: error(self, "has no next position set")
         if trace & TRACE_WHEELS: print(f'         moved {self.typename} {self.name} from {self.position} to {self.nextposition}')
         self.position = self.nextposition #move to where the Axle finger or another wheel or a carry pushed us
         self.nextposition = None

class DigitWheelCarry(DigitWheel): #a digit wheel with a carry warning arm
   def __init__(self, typename, digitstack, digitnum):
      DigitWheel.__init__(self, typename, digitstack, digitnum) #create the basic wheel
      self.carry_warned = False     #and add the carry state
   def movewheel(self, subtraction:bool):
      DigitWheel.movewheel(self, subtraction) #queue the movement as for any wheel
      if self.nextposition == (9 if subtraction else 0): #is it 0 to 9 for subtraction, or 9 to 0 for addition?
         self.carry_warned = True #if so, warn that a carry or borrow is needed to the cage above

class DigitStack(Component): #a stack of digit wheels, which might be interleaved with other such stacks on the same Axle
   def __init__(self, name, axle, withcarry):
      Component.__init__(self, "DigitStack", name)
      self.name = name
      self.wheels = [] #an ordered list of all its wheel objects
      for wn in range(NDIGITS+1): #create all the wheels, plus the sign wheel
         if withcarry:
            self.wheels.append(DigitWheelCarry("DigitWheelCarry", self, wn))
         else: self.wheels.append(DigitWheel("DigitWheel", self, wn))
      self.axle = axle; #a pointer to the Axle that goes through us
      self.finger_engaged = False; #is the Axle finger able to engage with this stack's wheel fingers?
      self.locked = True #are the wheels of this axle locked? (not yet implemented)
      self.meshed_axles = [] #the list of axles we are currently meshed to
   def axlemoved(self, fingerpos): 
      if self.finger_engaged: #if our finger is at the same level as the Axle's finger
         for wh in self.wheels: #see which wheels will advance one "unit of space"
            wh.checkfinger(fingerpos)
   #meta functions
   def _setvalue(self, number:int, print=True): #set a multi-digit number on the wheels
      if number < 0:
         self.wheels[NDIGITS].position = 1
         number = -number
      else: self.wheels[NDIGITS].position = 0
      for w in range(NDIGITS):
         self.wheels[w].position = number % 10
         number //= 10 
      if print: self._printvalue()
   def _printvalue(self): #display the number currently on the wheels
      print(self.name+": ", end="")
      if self.wheels[NDIGITS].position & 1: print("-", end="")
      for w in range(NDIGITS):
         print(self.wheels[NDIGITS-1-w].position, end="")
      print()
   def _value(self): #return the value on the wheel as an integer
       val = 0
       for w in range(NDIGITS): val = val*10 + self.wheels[NDIGITS-1-w].position
       if val+1 == 10**NDIGITS: val = 999999999 #TEMP to keep columnar displays neat
       if self.wheels[NDIGITS].position & 1: val = -val
       return val

all_axles = []  #a global list of all the axles
class Axle(Component): #an axle that goes through one or more interleaved DigitStacks and has fingers
   def __init__(self, name, numstacks, withcarry=False):
      Component.__init__(self, "Axle", name)
      all_axles.append(self) #add us to the list of all axles
      self.carriage = None #assume we have no carriage
      self.fingerpos = 0 #the Axle finger is just to the left of this digit position
      self.decrement = False #we are not decrementing our lowest digitstack
      self.digitstacks = [] #the list of all Digitstacks this Axle goes through
      for ndx in range(numstacks): #create them, perhaps with the first (lowest) having carriage
         self.digitstacks.append(DigitStack(name+"."+str(ndx), self, withcarry if ndx==0 else False)) 
   def advance(self): #rotate the Axle
      if self.driven: #if we are driven by the Prime Mover
         self.fingerpos -= 1 #move our fingers one "unit of space"
         if (self.fingerpos < 0): self.fingerpos = 9
         if self.decrement: #we are decrementing ourself by one as a special function
             lsb_wheel = self.digitstacks[0].wheels[0] #the units wheel of the first number in the cage
             lsb_wheel.movewheel(True)  #decrement it by one
             self.decrement = False #and that's all we need to do; carriage will happen later
         else: #we are "giving off"
             for digitstack in self.digitstacks: #drive all our DigitStacks
                digitstack.axlemoved(self.fingerpos) 

class AxleCarriage(Component): #a set of axles adjacent to an Axle that has digit wheels with carry arms
   #This is a pretty abstracted component that implements Babbage's Anticipating Carriage. We don't
   #attempt to model the detailed mechanism, only the timing of its effect on the adjacent digit wheels.
   #Be careful not to do something in a time unit that the real mechanical parts won't be able to do!
   def __init__(self, axle:Axle):
      Component.__init__(self, "Carriage", axle.name+".Carriage")
      self.axle = axle #remember the Axle we are adjacent to
      axle.carriage = self #and tell it we are its carriage
      self.carry_needed = [False for _ in range(NDIGITS)] #whether a carry is needed for each wheel
      self.running_up = False #whether the result is "running up": overflow for addition, or became negative for subtraction
   def compute_carriage(self, subtraction=False): #look at the adjacent digit axis and compute the necessary carries
      self.running_up = False
      wn = 0
      while wn < NDIGITS: #look for a wheel with a carry warning
         if self.axle.digitstacks[0].wheels[wn].carry_warned: #found one
            while wn < NDIGITS: #now look for a chain of following 9's (addition) or 0's (subtraction)
               wn += 1
               if wn < NDIGITS and self.axle.digitstacks[0].wheels[wn].position == (0 if subtraction else 9):
                  self.carry_needed[wn] = True #and flag each of them to be incremented or decremented
               else: break #chain ended
         else: wn += 1
   def do_carriage(self, subtraction=False): #execute the flagged carries
      for wn in range (NDIGITS):
         if self.axle.digitstacks[0].wheels[wn].carry_warned or self.carry_needed[wn]:
            if wn == NDIGITS-1: self.running_up = True #overflow for addition, negative for subtraction
            else: self.axle.digitstacks[0].wheels[wn+1].movewheel(subtraction)
            self.axle.digitstacks[0].wheels[wn].carry_warned = False #reset the carry indications
            self.carry_needed[wn] = False
            
def wheelmesh(axle:Axle, wheel_in_cage:int, shift=0, subtraction=False):
    #create the descriptor list for an axle we are meshed with
    return [axle, wheel_in_cage, shift, subtraction]
   
def show_meshes(msg):
    for axle in all_axles:
        for digitstack in axle.digitstacks:
            if digitstack.meshed_axles:
                for mesh in digitstack.meshed_axles:
                    print(f" {msg}, {digitstack.name} is meshed to {mesh[0].digitstacks[mesh[1]].name} shift {mesh[2]} subtract {mesh[3]}")
    
class Stud(Component): #this define the a stud on a barrel
#This is an unusual class in that every instance stores a pointer to an action function that is
#invoked by the barrel if the stud is on when the barrel advances and the current vertical takes effect.
    def __init__(self, name, studnum, action_fct, can_skip):
        Component.__init__(self, "Stud", name)
        self.studnum = studnum
        self.action_fct = action_fct
        self.can_skip = can_skip #can this stud, if ON, cause a +-1 extra skip?
        
class Barrel(Component):
   def __init__(self, name, program):
      Component.__init__(self, "Barrel", name)
      self.program = program
      self.reset(0)
   def reset(self, position): #reset the barrel to it's initial condition
      self.phase = 1 #we number phases 1 to 15 or 20
      self.barrel_position = position #barrel positions are numbered 0 to #verticals-1
      self.move_distance = 0  #how far the reducing apparatus says we should move
      self.doskip = False
      self.jump_backwards = False
      self.num_phases = 15 #assume a short cycle
   def advance(self): #this defines the sequence of operations during the 15 or 20 time units of a cycle
        vert = self.program.verticals[self.barrel_position]
        if trace & TRACE_BARRELS: print(f"         barrel vertical {self.barrel_position} phase {self.phase} at timeunit {timeunit}")
        if self.phase > 20: error(self, "phase > 20")
        
        '''Here's what happens in the various cycle phases from 1 to 15 or 20.
         (A lot of it happens in the functions that define the semantics of the studs.)
            2: set up the axle meshing and the jump direction
            4-12: do the "giving off" of the axles that are being driven
            meanwhile:  6-9: do the 4-position barrel move, if specified
                        10-11: do the 2-position barrel move, if specified
                        12: do the 1-position barrel move, if specified
            13: undo the axle meshing and finger engagement
            13-15: reserved for lockings
            for long cycles: 16: compute carries
                             17: execute carries
                             18: check "running up" and maybe do another 1-position move
                             18-20: reserved for locking
            '''
        #here's the core of the action...
        for studnum in vert: #in every phase, execute the action functions for all ON studs
            if studnum&1 == 0: #if it's an "on" stud
                stud = studlist[studnum]
                if stud.action_fct != None: stud.action_fct(self)
        if self.phase==3 and trace & TRACE_MESHES: 
            show_meshes(f"for vertical {self.barrel_position}")
        if self.phase >= 4 and self.phase <= 12: #this is the "giving off" time for driven axles
           for axle in all_axles: #so advance them
               add_to_advance_list(axle) #give all axles an opportunity to advance
        if self.phase==18 and self.doskip: # an additional skip was requested by some stud semantics
            self.move_distance += -1 if self.jump_backwards else +1 #so do it now
            
        self.phase += 1 #set up to go to the next phase (when we are activated at the next time unit)
        if self.phase > self.num_phases: #the cycle has ended
            if trace & TRACE_JUMPS and self.move_distance != 1:
                print(f"         jmp  {self.move_distance} from {self.barrel_position}, doskip={self.doskip} back={MOVEBACK.studnum in vert}")
            if trace & TRACE_BARRELS:
                #print(f"{timeunit:5} after vertical {self.barrel_position:2}: ", end="") #TEMP
                for axle in [A,B,C,D,E,F,G]: print(f"{axle.digitstacks[0]._value():12} ", end="")
                print()
            #move to the new vertical and start over with phase 1
            self.reset((self.barrel_position + self.move_distance) % len(self.program.verticals))
                                
awaiting_advance = [] #the list of components awaiting a time unit advance
timeunit = 0
seconds_per_timeunit = .157

def add_to_advance_list(comp): #add a component to the list of components awaiting advance
   if comp.driven: error(comp, " is already being driven") 
   #if trace & TRACE_ADVANCE: print(f"  adding {comp.name} to advance_list")
   awaiting_advance.append(comp) 
   comp.driven = True

def timeunit_tick(): #advance the simulator by one time unit
   global timeunit, trace
   timeunit += 1
   #if timeunit==201: trace=TRACE_ALL #TEMP
   #if timeunit>185: trace = TRACE_WHEELS #TEMP
   #if timeunit>200: trace = 0 #TEMP
   show_time = True
   while awaiting_advance: #advance all the components awaiting a state change by one time unit in a random order
      next_component = awaiting_advance.pop(random.randint(0,len(awaiting_advance)-1))
      if trace & TRACE_ADVANCE: print(f"{f'at {timeunit}' if show_time else '':6}", f"advancing {next_component.typename} {next_component.name}")
      if not next_component.driven: error(next_component, "is on the awaiting_advance list but is not driven")
      next_component.advance() #change its state
      next_component.driven = False
      show_time = False

'''          ****** STUD DEFINTIONS *******

The name of a stud is a global variable that in this module is a reference to the stud component.
The semantics of a stud that screwed into the "ON" position of the barrel is defined by
a function pointed to by the stud component. To create them we mostly use LAMBDA anonymous
functions in the call to create_stud() that creates the stud.

A stud's semantics function is called for each of the 15 or 20 phases of a barrel cycle,
and it gets to decide what action it takes when. For the general outline of the sequencing,
see the long comment inside the Barrel "advance" function.
'''
studnames = [] #a list of the stud names, each appearing twice: the ON version and the OFF version
studlist = []  #a list of references to the stud components, also each twice
studnum_moves = 999

def create_stud(name:str, action_fct=None, can_skip=False): #create a named stud 
   global studnum, studlist
   newstud = Stud(name, studnum, action_fct, can_skip)
   studlist.append(newstud) #create ON and OFF pointers to the stud components
   studlist.append(newstud)
   studnames.append(name) #create an ON and OFF copies of the stud names
   studnames.append(name)
   if studnum < studnum_moves: #for the disassembler,
       jumpstud(name, studnum) #let the assembler know about jump studs
   #Ok, dynamically creating global variables is not "Pythonic", but it
   #avoids having the barrel program cluttered with quoted strings for keywords
   globals()[name] = newstud #create the stud name, which is global to this module only
   studnum += 2
   
def chkmove(barrel, actionphase, distance): #the semantics of the MOVE4, MOVE2, and MOVE1 studs
    if barrel.phase == actionphase:
        barrel.move_distance += -distance if barrel.jump_backwards else +distance
 
def setbackwards(barrel): #the semantics of the MOVEBACK stud
    if barrel.phase == 2: #when we do the axle meshing setup
        barrel.jump_backwards = True #set the pinion that "reduces" the barrel backwards
    
def initialize_studs(): #initialize the stud list with the standard ones for jumps
    global studnum, studnum_moves
    studnum = 0
    #the studs involved with jumps need to be at the beginning
    create_stud("MOVE1",    lambda barrel: chkmove(barrel, 12, 1)) #use phases 12 to move 1
    create_stud("MOVE2",    lambda barrel: chkmove(barrel, 10, 2)) #use phases 10,11 to move 2
    create_stud("MOVE4",    lambda barrel: chkmove(barrel, 6, 4))  #use phases 6,7,8,9 to move 4
    create_stud("MOVEBACK", lambda barrel: setbackwards(barrel)) 
    studnum_moves = studnum #note the end of the jump studs
 
#*****  tests *****

trace = 0  #what trace output we want: TRACE_ADVANCE, TRACE_WHEELS, TRACE_BARRELS, TRACE_MESHES, TRACE_JUMPS
#trace = TRACE_ALL
#trace = TRACE_BARRELS

if True: #test a barrel program to do unsigned multiplication
    A =  Axle("A",NPERCAGE)  #create the axles we need
    B =  Axle("B",NPERCAGE, withcarry=True) #this one has carry warning arms for its first number in its cages
    BC = AxleCarriage(B) #create an Anticipating Carriage mechanism adjacent to it
    C =  Axle("C",NPERCAGE) 
    D =  Axle("D",NPERCAGE) 
    E =  Axle("E",NPERCAGE, withcarry=True) 
    EC = AxleCarriage(E) #E is a seecond anticipating carriage
    F =  Axle("F",NPERCAGE) 
    G =  Axle("G",NPERCAGE) 
      
    #define the studs we use for the multiplication barrel, and their semantics
    
    #the semantics of all studs that cause one number column to mesh with another,
    # which includes GIVEOFF, ADD, SUB, SHL, and SHR
    #(TODO: make it work for numbers stored on other than the first one in the cage)
    def mesh(barrel, fromAxle:Axle, toAxle:Axle, shift=0, subtract=False): 
       if barrel.phase == 2: #do the meshing
            fromAxle.digitstacks[0].finger_engaged = True #engage the axle finger with the lower digits in the cages
            fromAxle.fingerpos = 9 #start the axle finger at position 9
            fromAxle.digitstacks[0].meshed_axles.append(wheelmesh(toAxle, 0, shift=shift, subtraction=subtract)) #mesh "from" with "to"
            if trace & TRACE_MESHES: print(f"        mesh {fromAxle.name} to {toAxle.name}")
       if barrel.phase == 13:
           fromAxle.digitstacks[0].finger_engaged = False #disengage from the digit stack
           fromAxle.digitstacks[0].meshed_axles = [] #unmesh from all axles
       if toAxle.carriage != None:
            if barrel.phase == 16: toAxle.carriage.compute_carriage()
            if barrel.phase == 17: toAxle.carriage.do_carriage(subtract)
      
    #the semantics of DECR, which decrements an axis by one without giving off to any other column
    def decr(barrel, axle:Axle):
        if barrel.phase == 2:
            axle.decrement = True #tell it to decrement once
            axle.digitstacks[0].finger_engaged = False #and we aren't giving off
        if barrel.phase == 16: axle.carriage.compute_carriage()
        if barrel.phase == 17: axle.carriage.do_carriage(True) 
        
    #the semantics of ZERO, which "gives off" a column without meshing, just so that it becomes zero
    def zero(barrel, axle:Axle):
        if barrel.phase == 2:
            axle.digitstacks[0].finger_engaged = True #we are giving off, meshed to no one
            axle.fingerpos = 9 #start the axle finger at position 9
        if barrel.phase == 13:
            axle.digitstacks[0].finger_engaged = False #disengage from the digit stack
            
    #the stud that specifies this vertical as a long (20 time unit) cycle
    def set_longcycle(barrel):
        if barrel.phase == 2: barrel.num_phases = 20
        
    #the semantics of the testing for a "running up" condition after carriage,
    #which causes an extra +-1 turn of the reducing apparatus of the barrel
    def chk_runup(barrel, carriage:AxleCarriage, invert:bool):
        if barrel.phase == 18 and carriage.running_up ^ invert:
            barrel.doskip = True
      
    #the STOP stud      
    def dostop(barrel): 
        global stopped
        if barrel.phase == 2: stopped = True
            
    initialize_studs() 
    create_stud("GIVE_C_TO_E",    lambda barrel: mesh(barrel, C, E))
    create_stud("GIVE_D_TO_G",    lambda barrel: mesh(barrel, D, G))
    create_stud("GIVE_A_TO_D",    lambda barrel: mesh(barrel, A, D))
    create_stud("GIVE_D_TO_A",    lambda barrel: mesh(barrel, D, A))
    create_stud("GIVE_G_TO_C",    lambda barrel: mesh(barrel, G, C))
    create_stud("SHR_C_TO_D",     lambda barrel: mesh(barrel, C, D, shift=-1)) 
    create_stud("SHL_D_TO_F",     lambda barrel: mesh(barrel, D, F, shift=+1))
    create_stud("SHL_A_TO_D",     lambda barrel: mesh(barrel, A, D, shift=+1))
    create_stud("ADD_A_TO_B",     lambda barrel: mesh(barrel, A, B))
    create_stud("ADD_G_TO_E",     lambda barrel: mesh(barrel, G, E))
    create_stud("SUB_F_FROM_E",   lambda barrel: mesh(barrel, F, E, subtract=True))
    create_stud("DECR_E",         lambda barrel: decr(barrel, E))
    create_stud("ZERO_E",         lambda barrel: zero(barrel, E))
    create_stud("IF_RUNUP_EC",    lambda barrel: chk_runup(barrel, EC, False), can_skip=True)
    create_stud("IF_NORUNUP_EC",  lambda barrel: chk_runup(barrel, EC, True), can_skip=True)
    create_stud("CYCLE20",      lambda barrel: set_longcycle(barrel))
    create_stud("STOP",           lambda barrel: dostop(barrel))

    mulpgm = program("multiply program", studnames) #create and assemble the program
    mulpgm.vertical("outerloop",  SHR_C_TO_D, GIVE_C_TO_E)
    mulpgm.vertical(              SHL_D_TO_F, GIVE_D_TO_G)
    mulpgm.vertical(              SUB_F_FROM_E, GIVE_A_TO_D, CYCLE20) 
    mulpgm.vertical("innerloop",  GIVE_D_TO_A, DECR_E, CYCLE20, IF_RUNUP_EC,  "doadd")
    mulpgm.vertical("doadd",      ADD_A_TO_B, GIVE_A_TO_D, CYCLE20,  "innerloop")
    mulpgm.vertical(              SHL_A_TO_D)
    mulpgm.vertical(              GIVE_D_TO_A, ADD_G_TO_E, GIVE_G_TO_C, CYCLE20, IF_NORUNUP_EC,  "zero_e")
    mulpgm.vertical("zero_e",     ZERO_E,  "outerloop")
    mulpgm.vertical(              STOP)
    mulpgm.end_program()
    mulpgm.disassemble()
    mulpgm.showverticals()
    
    BARMUL = Barrel("BARMUL", mulpgm) #create a barrel with that program on it
    
    def domult(x, y): #multiply A x C and put the product in B
        global stopped, timeunit, awaiting_advance
        BARMUL.reset(0) #reset the barrel to initial conditions
        A.digitstacks[0]._setvalue(x, print=False) #put the input operands on their axes
        C.digitstacks[0]._setvalue(y, print=False) 
        for axle in [B,D,E,F,G]: axle.digitstacks[0]._setvalue(0, print=False) #zero the temporary axes
        print(f"multiplying {x} by {y}")
        stopped = False
        timeunit = 0
        awaiting_advance = []
        while not stopped: #until the barrel stops us
            add_to_advance_list(BARMUL) #start each time unit by advancing only the barrel state
            timeunit_tick() #process state changes until there are no more
        print(f"done in {timeunit} time units, or {timeunit*seconds_per_timeunit/60:.2f} minutes")  
        #B.digitstacks[0]._printvalue()
        answer=B.digitstacks[0]._value()
        print(f"product is {answer} {'' if x*y==answer else 'WRONG!'}")
        print()
       
    domult(123,12)
    domult(123456,12)
    domult(123456, 0)
    domult(0,12)
    domult(123,56)
    domult(123456,123456)
    domult(123,11111111)
    