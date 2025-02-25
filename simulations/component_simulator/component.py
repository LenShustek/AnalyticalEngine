'''file: component.py
    
    ******  A COMPONENT-LEVEL SIMULATOR FOR THE ANALYTICAL ENGINE  *******

This simulates the engine at a resolution of basic "time units", 15 or 20 of which comprise a "cycle".
The activities during a cycle are controlled by the current "verticals" on the microprogram barrels.

The model is of an interconnected assembly of hierarchical "components" that have internal state. 
The components are:
   - digit wheels with gears, and stacks thereof
   - axles that go through one or more interleaved stacks of digit wheels
   - anticipating carriage for an axle
   - pinion gears, and stacks thereof
   - counters
   - barrels
Still to do:
    - racks to connect the Store and the Mill
    - card readers for operation, number, and variable cards
     
Some components, like digit wheels, are eligible to change state sometime during a time unit, and they have an 
"advance" function that is called to do that. Other components are only conduits for state changes between other
components. For example, a "stack of digit wheels" is the conduit to transmit a state change from in the axle it
is on to all the wheels in the stack, some of which will then having pending state changes of their own.

We use the following process to try to emulate the parallelism in the engine:

1. Start by putting onto an "awaiting_advance" list the components that are eligible to be driven in some way
   by the Prime Mover. This is typically only the barrel, which then adds lifted driven wheel axles to that list.

2. Continually remove a random one of those components from the list and call its "advance" function so that
   it changes internal state based on its current state, as appropriate for a duration of one time unit.

3. When a component's current state changes, it is eligible to also create pending state changes in other components
   to which it is currently connected, perhaps indirectly throught a conduit. It then adds those components to the 
   "awaiting_advance" list so that those state changes will occur at a random time during the current time unit. 
   Here are some examples:
   - a turning digit wheel is meshed to a pinion, and so directly causes it to turn
   - a rotating axle has a finger that may be in position to impinge (using a stack of digit wheels as a conduit) 
     on the finger of one if its wheels, and so turns it
   - a turning pinion is meshed to two others and causes them to turn

4. When the "awaiting_advance" list finally becomes empty, all the actions for this time unit are over.
   Increment to the next time unit and go to step 1.

The purpose of the randomization in step 2 is to reveal if there are any race conditions that depend on the 
order in which component state changes are done. It's not a proof, but making many runs with different 
orderings should help flush out problems. 

29 Dec 2023, L. Shustek, started
16 Feb 2025, L. Shustek, major revision to model all gears and pinions and the way they mesh
'''
import random
import traceback
from barrel_assembler import program, jumpstud

NDIGITS=25   # of digits in each number of a column, not including the sign
NPERCAGE=2   # of digits in a cage, ie how many numbers a column holds

CCW = True   # direction of gear motion
CW = False  

TRACE_ADVANCE, TRACE_WHEELS, TRACE_GEARS, TRACE_QUEUES, TRACE_BARRELS, TRACE_MESHES, TRACE_JUMPS, TRACE_VALUES, TRACE_ENDING_VALUES = \
    1,2,4,8,16,32,64,128,256  #flags for which tracing output we want
TRACE_ALL = -1 

def error(thing, msg:str):
   print("ERROR: ", end="")
   if isinstance(thing, Component): print(f"{thing.typename} {thing.name} ", end="")
   if isinstance(thing, str): print(thing, end="")
   print(msg, "at timeunit", timeunit)
   traceback.print_stack()
   exit()

def DIRstr(direction):
    return "CCW" if direction == CCW else "CW"

###########  components  ############

class Component: #every part that might be acted upon is a Component
   def __init__(self, typename:str, name:str):
      self.typename = typename
      self.name = name

all_gears = [] 
class Gear(Component): #a circular gear (on a pinion or digit wheel) that can mesh with others
    def __init__(self, typename, name):
       Component.__init__(self, typename, name)
       all_gears.append(self)
       self.direction = CCW #the direction we're moving
       self.driving_gear = self #the gear that is driving us, if any
       self.meshes = [] #a list of all rotating objects (pinions or wheels) we are currently meshed with
        
all_pinions_and_wheels = [] 
class Pinion(Component): #a pinion gear that can mesh with other gears, perhaps conditionally
    def __init__(self, typename, pinionstack, pinionnum):
       Component.__init__(self, typename, pinionstack.name+".P"+str(pinionnum))
       all_pinions_and_wheels.append(self) #add us to the list of all pinions and wheels
       self.pinionstack = pinionstack
       self.gear = Gear("PinionGear", pinionstack.name+".G"+str(pinionnum)) #our gear
       self.driven = False #are we being driven by something
       self.vposition = 0 #our current vertical position
       self.mesh_vposition = [] #possible vertical positions
       self.mesh_object = [] #what objects (pinions or wheels) are meshed with in that case
    def define_mesh(self, vposition, object): #define a possible mesh
        self.mesh_vposition.append(vposition) #if we're at this position
        self.mesh_object.append(object) #we are meshed to this object
    def meshed_rotate(self, direction):
        self.gear.direction = direction
        add_to_advance_list(self, direction) 
    def advance(self, direction): #rotate a pinion gear
        self.direction = direction #TEMP need to do this?
        if trace & TRACE_GEARS: print(f'         rotated {self.typename} {self.name} {DIRstr(self.direction)} ')
        rotate_meshed_gears(self.gear) # queue movement of all objects (pinions or wheels) meshed with our gear
  
all_pinionstacks = []  
class PinionStack(Component): #a stack of pinions, that perhaps can move vertically
    def __init__(self, name, number):
      Component.__init__(self, "PinionStack", name)
      all_pinionstacks.append(self) #add us to the list of all pinion stack
      self.name = name
      self.pinions = [] #an ordered list of all its pinion objects
      for pn in range(number): #create all the pinions
         self.pinions.append(Pinion("Pinion", self, pn))
    def define_mesh(self, position, object, shift=0):  #define meshes based on vertical position
        for ndx in range(len(self.pinions)):
            if ndx+shift >= 0 and ndx+shift < len(self.pinions):
                self.pinions[ndx].define_mesh(position, object[ndx+shift])
    def lift(self, vposition): #lift all gears in the stack to a specified vertical position
        for pn in self.pinions:
            pn.vposition = vposition
       
class DigitWheel(Component): #a basic digit wheel
# it can be moved conditionally by a finger on its axle that impinges on the finger of the wheel,
# or unconditionally because the Anticipating Carriage is handing us a carry, or
# because we're being incremented or decremented by 1
   def __init__(self, typename, digitstack, digitnum):
       Component.__init__(self, typename, digitstack.name+".W"+str(digitnum))
       all_pinions_and_wheels.append(self) #add us to the list of all pinions and wheels
       self.gear = Gear("DigitWheelGear", digitstack.name+".G"+str(digitnum))
       self.driven = False #are we being driven by something
       self.mesh_vposition = [] #possible vertical positions
       self.digitstack = digitstack
       self.digitnum = digitnum # 0 is least significant
       self.whposition = 0 #current rotational position: 0 to 9
       self.nextwhposition = None
   def meshed_rotate(self, direction):
       self.gear.direction = direction
       if not (self.nextwhposition is None): error(self, "already has position set")
       if direction == CCW:
           self.nextwhposition = self.whposition-1; 
           if self.nextwhposition < 0: self.nextwhposition = 9
       else: #CW
           self.nextwhposition = self.whposition+1;
           if self.nextwhposition > 9: self.nextwhposition = 0
       add_to_advance_list(self, direction)
   def queue_movewheel(self, position): #queue us to have a wheel movement to "position"
        if trace & TRACE_QUEUES: print(f'         queuing move of {self.typename} {self.name} from {self.whposition} to {position}')
        if (position+1)%10 != self.whposition and (position-1)%10 != self.whposition:
            error(self, "is attempting to move more than one position")
        self.nextwhposition = position;
        add_to_advance_list(self, CCW) #add ourselves to the list of pending advances during this time unit
   def checkfinger(self, fingerpos): #our axle's finger just moved
        if (fingerpos + 1) % 10 == self.whposition: #it had been at our position
            self.queue_movewheel(fingerpos) #so we will schedule a move to where the axle finger is now
            return True
        else: return False #this wheel doesn't (yet) move
   def movewheel(self, direction): #schedule an unconditional move for a carry or borrow
      self.gear.direction = direction;
      self.queue_movewheel((self.whposition + (-1 if direction == CCW else +1)) % 10)  #either same or opposite direction
   def advance(self, direction): #manifest a queued change in wheel position
         self.gear.direction = direction #TEMP need to do this?
         if self.nextwhposition is None: 
             error(self, "has no next position set")
         if trace & TRACE_WHEELS: 
             print(f'         moved {self.typename} {self.name} {DIRstr(self.gear.direction)} from {self.whposition} to {self.nextwhposition}')
         self.whposition = self.nextwhposition #move to where the Axle finger or another wheel or a carry pushed us
         self.nextwhposition = None
         self.digitstack.changed = True #note that the value on this digit stack has changed
         rotate_meshed_gears(self.gear) # queue movement of all objects meshed with our gear

class DigitWheelCarry(DigitWheel): #a digit wheel with a carry warning arm attached (for the anticiating carriage)
   def __init__(self, typename, digitstack, digitnum):
      DigitWheel.__init__(self, typename, digitstack, digitnum) #create the basic wheel
      self.carry_warned = False     #and add the carry state
   def advance(self,direction):
       DigitWheel.advance(self, direction) #do the action as for any wheel
       if not self.digitstack.doing_carries:
           if self.whposition == (9 if direction == CCW else 0): #is it 0 to 9 for subtraction, or 9 to 0 for addition?
               self.carry_warned = True #if so, warn that a carry or borrow is needed to the cage above
        
class DigitStack(Component): #a stack of digit wheels, which might be interleaved with other such stacks on the same Axle
   def __init__(self, name, axle, withcarry):
      Component.__init__(self, "DigitStack", name)
      self.name = name
      globals()[name] = self #create a global variable with our name, for convenience in _setvalue, etc.
      self.wheels = [] #an ordered list of all its wheel objects
      for wn in range(NDIGITS+1): #create all the wheels, plus the sign wheel
         if withcarry:
            self.wheels.append(DigitWheelCarry("DigitWheelCarry", self, wn))
         else: self.wheels.append(DigitWheel("DigitWheel", self, wn))
      self.axle = axle; #a pointer to the Axle that goes through us
      self.locked = True #are the wheels of this axle locked? (not yet implemented)
      self.count_by_1 = False #we are not decrementing our lowest digitstack
      self.doing_carries = False; #we are not doing carries
      self.changed = False #for debugging: has the value changed?
      self.meshed_axles = [] #the list of axles we are currently meshed to
   def advance(self, direction):
       if trace & TRACE_ADVANCE: print(f' advancing digitstack {self.name}')
       if self.count_by_1: #we are being incremented or decremented by 1
           lsb_wheel = self.wheels[0] #the units wheel of the first number in the cage
           #lsb_wheel.gear.direction = CCW; the direction is now set by count1()
           lsb_wheel.movewheel(lsb_wheel.gear.direction)  #increment or decrement it by one
           self.count_by_1 = False;
       else: #we are "giving off" our value
            for wh in self.wheels: #see which wheels will advance one "unit of space"
                wh.checkfinger(self.axle.fingerpos)
 #DigitStack meta functions
   def _setvalue(self, number:int, print=True): #set a multi-digit number on the wheels
      if number < 0:
         self.wheels[NDIGITS].whposition = 1
         number = -number
      else: self.wheels[NDIGITS].whposition = 0
      for w in range(NDIGITS):
         self.wheels[w].whposition = number % 10
         number //= 10 
      if print: self._printvalue()
   def _printvalue(self): #display the number currently on the wheels
      print(self.name+": ", end="")
      if self.wheels[NDIGITS].whposition & 1: print("-", end="")
      for w in range(NDIGITS):
         print(self.wheels[NDIGITS-1-w].whposition, end="")
      print()
   def _value(self): #return the value on the wheel as an integer
       val = 0
       for w in range(NDIGITS): val = val*10 + self.wheels[NDIGITS-1-w].whposition
       if val+1 == 10**NDIGITS: val = 999999999 #TEMP to keep columnar displays neat
       if self.wheels[NDIGITS].whposition & 1: val = -val
       return val
   
all_axles = [] 
class Axle(Component): #an axle that goes through one or more interleaved DigitStacks and has fingers
   def __init__(self, name, numstacks, withcarry=False):
      Component.__init__(self, "Axle", name)
      all_axles.append(self) #add us to the list of all axles
      self.driven = False; #are we driven by the Prime Mover?
      self.carriage = None #assume we have no carriage
      self.fingerheight = 0 #the height of the finger
      self.fingerpos = 9 #the Axle finger is just before this digit position
      self.digitstacks = [] #the list of all Digitstacks this Axle goes through
      for ndx in range(numstacks): #create them, perhaps with the first (lowest) having carriage
         self.digitstacks.append(DigitStack(name+str(ndx+1) if numstacks > 1 else name, self, withcarry if ndx==0 else False)) 
   def lift(self, vposition): #lift the fingers in the stacks to a specified vertical position
       self.fingerheight = vposition
   def advance(self, direction): #rotate the Axle
      if self.driven: #if we are driven by the Prime Mover
          self.fingerpos -= 1 #move our fingers one "unit of space"
          if (self.fingerpos < 0): self.fingerpos = 9
          if self.fingerheight == DIGITFINGER_DISTANCE or self.digitstacks[0].count_by_1:
             self.digitstacks[0].advance(direction)
          elif self.fingerheight == -DIGITFINGER_DISTANCE: #just moving fingers, not wheels
             self.digitstacks[1].advance(direction)
 #Axle meta functions that are useful for carriage axes that have only one digitstack
   def _setvalue(self, number:int, print=True):
      self.digitstacks[0]._setvalue(number, print)
   def _printvalue(self):
      self.digitstacks[0]._printvalue()   
   def _value(self):
      return self.digitstacks[0]._value()     

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
   def compute_carriage(self, direction): #look at the adjacent digit axis and compute the necessary carries
      self.running_up = False
      self.direction = direction
      wn = 0
      while wn < NDIGITS: #look for a wheel with a carry warning
         if self.axle.digitstacks[0].wheels[wn].carry_warned: #found one
            while wn < NDIGITS: #now look for a chain of subsequent 9's (addition) or 0's (subtraction)
               wn += 1
               if wn < NDIGITS and self.axle.digitstacks[0].wheels[wn].whposition == (0 if direction == CCW else 9):
                  self.carry_needed[wn] = True #flag each of them to be incremented or decremented
               else: break #chain ended
         else: wn += 1
   def do_carriage(self, direction): #execute the flagged carries
      for wn in range (NDIGITS):
         if self.axle.digitstacks[0].wheels[wn].carry_warned or self.carry_needed[wn]:
            if wn == NDIGITS-1: self.running_up = True #overflow for addition, negative for subtraction
            else: self.axle.digitstacks[0].wheels[wn+1].movewheel(direction)
            self.axle.digitstacks[0].wheels[wn].carry_warned = False #reset the carry indications
            self.carry_needed[wn] = False
            self.axle.digitstacks[0].doing_carries = True #prevent additional carry warning from carries

class Counter(Component): # an abstract component that can count from 0 to NDIGITS
    def __init__(self, name):
        Component.__init__(self, "Counter", name)
        self.driven = False
        self.value = 0
        self.running_up = False
    def clear(self):
        self.value = 0
        self.running_up = False
    def advance(self, direction):
        self.driven = False
        if direction == CCW:
            self.value -= 1
            if self.value < 0: 
                self.value = NDIGITS
                self.running_up = True
        else:
            self.value += 1
            if self.value > NDIGITS: 
                self.value = 0
                self.running_up = True
    
##### functions for meshing gears

ALWAYS = 99 
def show_possible_meshes(): 
    for pn in all_pinions_and_wheels:
        if pn.mesh_vposition:
            print("possible meshes for "+pn.name)
            for ndx in range(len(pn.mesh_vposition)):
                vpos = pn.mesh_vposition[ndx]
                print(f'   position {"any" if vpos == ALWAYS else vpos} meshes with {pn.mesh_object[ndx].name}')

def compute_meshes(show=False): #current meshes, depending on vertical axle positions
    for pn in all_pinions_and_wheels:
        for ndx in range(len(pn.mesh_vposition)):
            vpos = pn.mesh_vposition[ndx]
            object = pn.mesh_object[ndx]
            if type(object) != Pinion and type(object) != DigitWheel and type(object) != DigitWheelCarry:
                error(object, "wrong object type when computing meshes")
            if vpos == ALWAYS or vpos == pn.vposition: #this mesh is active
                pn.gear.meshes.append(object) #we are meshed with it
                object.gear.meshes.append(pn) #and it is meshed with us
    if show: show_all_meshes()
    
def remove_meshes():
    for gear in all_gears: #clear all mesh gear lists
        gear.meshes = [] 
  
def show_all_meshes():
    for gear in all_gears:
        if gear.meshes:
            print(f'gear {gear.name} meshes: ', end="")
            for meshedobject in gear.meshes:
                print(f' {meshedobject.name} ', end="")
            print()             

def rotate_meshed_gears(driven_gear): #a gear just moved: queue all undriven objects meshed to it for movememn
    if trace & TRACE_QUEUES: print(f'     queuing objects meshed to gear {driven_gear.name}')
    for meshedobject in driven_gear.meshes:
        if meshedobject.driven and meshedobject.gear != driven_gear.driving_gear: #driven by someone other than us: conflict
            error(meshedobject, f" is a candidate for meshing by {driven_gear.name} but is already being driven by {driven_gear.driving_gear.name}") 
        if not meshedobject.driven:
            meshedobject.gear.driving_gear = driven_gear #record the gear doing the driving
            meshedobject.meshed_rotate(not driven_gear.direction) #queue rotation is the opposite direction
       
######  microprogram barrels  #########    

awaiting_advance = [] #the list of components awaiting a time unit advance
timeunit = 0
timelimit = 0
cycle = 0
seconds_per_timeunit = .157
trace = 0  #what trace output we want
       
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
      global cycle
      cycle += 1 #count cycles
      self.driven = False
      self.phase = 1 #we number phases 1 to 15 or 20
      self.barrel_position = position #barrel positions are numbered 0 to #verticals-1
      self.move_distance = 0  #how far the reducing apparatus says we should move
      self.doskip = False
      self.jump_backwards = False
      self.num_phases = 15 #assume a short cycle
   def advance(self, direction): #this defines the sequence of operations during the 15 or 20 time units of a cycle
        self.driven = False; #we are retriggered in the main outer loop
        vert = self.program.verticals[self.barrel_position]
        #if trace & TRACE_BARRELS: print(f"         barrel vertical {self.barrel_position} phase {self.phase} at timeunit {timeunit}")
        if self.phase > 20: error(self, "barrel phase > 20")
        
        '''Here's what happens in the various cycle phases from 1 to 15 or 20.
         Much of it happens in the functions that define the semantics of the studs.
            1-3: do unlocking
            2: do axle lifting, and set jump direction
            3: do meshes
            4-12: do the "giving off" of the axles that are being driven
            meanwhile:  6-9: do the 4-position barrel move, if specified
                        10-11: do the 2-position barrel move, if specified
                        12: do the 1-position barrel move, if specified
            13: undo the axle meshing and finger engagement
            14: "give off" axles being driver to restore fingers to the default position
            13-15: do locking
            for long cycles: 16: compute carries
                             17: execute carries
                             18: check "running up" and maybe do another 1-position move
                             18-20: do locking
            '''
        if self.phase == 1 and trace & TRACE_BARRELS:
            print(f"vertical {vertical_name(self, self.barrel_position)} starting at time {timeunit}") 
            pass
        for studnum in vert: #in every phase, execute the action functions for all ON studs
            if studnum&1 == 0: #if it's an "on" stud
                stud = studlist[studnum]
                if stud.action_fct != None: stud.action_fct(self)
        #now do phase-dependent global operations        
        if self.phase==3: #implement the gear meshing based on what was lifted
            compute_meshes()
        if self.phase >= 4 and self.phase <= 12: #this is the "giving off" time for driven axles
           for axle in all_axles: #so advance them
               if axle.driven:
                   add_to_advance_list(axle, CCW) #give all axles an opportunity to advance
        if self.phase == 13: #unmesh the gears
            remove_meshes()
        if self.phase == 14: #advance fingers on driven axles to be ready for the next giving-off
            for axle in all_axles:
                if axle.driven:
                    add_to_advance_list(axle, CCW)
        if self.phase==18 and self.doskip: # an additional skip was requested by some stud semantics
            self.move_distance += -1 if self.jump_backwards else +1 #so do it now
            
        self.phase += 1 #set up to go to the next phase when we are activated at the next time unit
        if self.phase > self.num_phases: #if this ends the cycle
            if trace & TRACE_ENDING_VALUES: show_changed_values()
            if trace & TRACE_JUMPS and self.move_distance != 1:
                print(f"      jmp from {vertical_name(self, self.barrel_position)} to {vertical_name(self, self.barrel_position + self.move_distance)}, doskip={self.doskip} back={MOVEBACK.studnum in vert}")
            if trace & TRACE_BARRELS:
                print(f"vertical {vertical_name(self, self.barrel_position)} done at time {timeunit}") 
            #move to the new vertical and start over with phase 1
            self.reset((self.barrel_position + self.move_distance) % len(self.program.verticals))
                                
def show_advance_list():
    if len(awaiting_advance) == 0:
        print("<empty>")
    else:
        for comp in awaiting_advance:
            print(f' {comp[0].name} ', end="")
        print()
    
def add_to_advance_list(comp, direction): #add a component (pinion or wheel) to the list awaiting advance
   if trace & TRACE_ADVANCE: 
       print(f"  adding {comp.name} {DIRstr(direction)} to advance_list ", end="")
       show_advance_list()
   comp.direction = direction
   if type(comp) != Axle and comp.driven: error(comp, f"is already driven by {comp.gear.driving_gear.name}")
   comp.driven = True
   awaiting_advance.append((comp, direction)) 

def show_changed_values():
 for axle in all_axles:
    for stack in axle.digitstacks:
        if stack.changed: 
            stack._printvalue()
            stack.changed = False   
    
def timeunit_tick(): #advance the simulator by one time unit
   global timeunit, trace, timelimit
   timeunit += 1
   if timelimit > 0 and timeunit > timelimit:
       print("time limit reached")
       exit()
   show_time = True
   steps = 0
   while awaiting_advance: #advance all the components awaiting a state change by one time unit in a random order
      (next_component, next_direction) = awaiting_advance.pop(random.randint(0,len(awaiting_advance)-1))
      if trace & TRACE_ADVANCE: 
          print(f"{f'at {timeunit}' if show_time else '':6}", f"advancing {next_component.typename} {next_component.name}, list:", end="")
          show_advance_list()
      if not next_component.driven: error(next_component, "is on the awaiting_advance list but is not driven")
      next_component.advance(next_direction) #change its state
      #if type(next_component) != Axle: next_component.driven = False 
      show_time = False
   if trace & TRACE_VALUES: show_changed_values()
       
   for object in all_pinions_and_wheels:
       object.driven = False

def vertical_name(barrel, vertical):
    result = f'{vertical}'
    for name, lab in barrel.program.labels.items():
        if lab.vndx == vertical: 
            result += f' ({name})'
    return result
     
''' ########  STUD DEFINTIONS  #########

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

########  the Plan 27 configuration  #########

DIGITMESH_DISTANCE = 0.4 # how far connecting pinions from digitwheels to long pinions move
LONGPINION_DISTANCE = 0.4 # how far movable long pinions move for shifting
REVERSE_PINION_DISTANCE = 0.3 #how far carriage wheel reversing pinions move to engage
FC_DISTANCE = 0.3 #how far FC moves to engage F when reversing, or twice this if not reversing
DIGITFINGER_DISTANCE = 0.4 #how far up or down a digit finger height changes to engage a digit wheel

# define the axles and pinion stacks, and the meshes possible between their gears baseed on lifts
# see Babbage's drawing BAB/A/093, or our Solidworks labeled simplified plan drawing
A = Axle("A",NPERCAGE)  #A1 and A2 digit wheels
P11 = PinionStack("P11", NDIGITS) #pinions connecting from A to MP
P12 = PinionStack("P12", NDIGITS) #pinions connecting from A to FP
MP1 = PinionStack("MP1", NDIGITS) #movable long pinions between A and B
FP1 = PinionStack("FP1", NDIGITS) #fixed long pinions between A and B
P13 = PinionStack("P13", NDIGITS) #pinions connecting from MP to B
P14 = PinionStack("P14", NDIGITS) #pinions connecting from FP to B
B = Axle("B", NPERCAGE)  #B1 and B2 digit wheels
P11.define_mesh(DIGITMESH_DISTANCE, A.digitstacks[0].wheels)
P11.define_mesh(-DIGITMESH_DISTANCE, A.digitstacks[1].wheels)
P11.define_mesh(ALWAYS, MP1.pinions) # connectors are always connected to the long pinions
MP1.define_mesh(0, FP1.pinions) # long pinions are normally always connected to each other 
MP1.define_mesh(LONGPINION_DISTANCE, FP1.pinions, shift=1) # but might be shifted up
P12.define_mesh(DIGITMESH_DISTANCE, A.digitstacks[0].wheels)
P12.define_mesh(-DIGITMESH_DISTANCE, A.digitstacks[1].wheels)
P12.define_mesh(ALWAYS, FP1.pinions) # connectors are always connected to the long pinions
P13.define_mesh(DIGITMESH_DISTANCE, B.digitstacks[0].wheels)
P13.define_mesh(-DIGITMESH_DISTANCE, B.digitstacks[1].wheels)
P13.define_mesh(ALWAYS, MP1.pinions) # connectors are always connected to the long pinions
P14.define_mesh(DIGITMESH_DISTANCE, B.digitstacks[0].wheels)
P14.define_mesh(-DIGITMESH_DISTANCE, B.digitstacks[1].wheels)
P14.define_mesh(ALWAYS, FP1.pinions) # connectors are always connected to the long pinions
P21 = PinionStack("P21", NDIGITS) #pinions connecting from B to MP
P22 = PinionStack("P22", NDIGITS) #pinions connecting from B to FP
MP2 = PinionStack("MP2", NDIGITS) #movable long pinions between B and C
FP2 = PinionStack("FP2", NDIGITS) #fixed long pinions between B and C
P23 = PinionStack("P23", NDIGITS) #pinions connecting from MP to C
P24 = PinionStack("P24", NDIGITS) #pinions connecting from FP to C
C = Axle("C", NPERCAGE)  #C1 and C2 digit wheels
P21.define_mesh(DIGITMESH_DISTANCE, B.digitstacks[0].wheels)
P21.define_mesh(-DIGITMESH_DISTANCE, B.digitstacks[1].wheels)
P21.define_mesh(ALWAYS, MP2.pinions) # connectors are always connected to the long pinions
MP2.define_mesh(0, FP2.pinions) # long pinions are normally always connected to each other 
MP2.define_mesh(LONGPINION_DISTANCE, FP2.pinions, shift=1) # but might be shifted up
P22.define_mesh(DIGITMESH_DISTANCE, B.digitstacks[0].wheels)
P22.define_mesh(-DIGITMESH_DISTANCE, B.digitstacks[1].wheels)
P22.define_mesh(ALWAYS, FP2.pinions) # connectors are always connected to the long pinions
P23.define_mesh(DIGITMESH_DISTANCE, C.digitstacks[0].wheels)
P23.define_mesh(-DIGITMESH_DISTANCE, C.digitstacks[1].wheels)
P23.define_mesh(ALWAYS, MP2.pinions) # connectors are always connected to the long pinions
P24.define_mesh(DIGITMESH_DISTANCE, C.digitstacks[0].wheels)
P24.define_mesh(-DIGITMESH_DISTANCE, C.digitstacks[1].wheels)
P24.define_mesh(ALWAYS, FP2.pinions) # connectors are always connected to the long pinions
R1 = PinionStack("R1", NDIGITS) #reversing pinions for F1
FC1 = PinionStack("FC1", NDIGITS) #connection pinions for F1
F1 = Axle("F1", 1, withcarry=True) #carriage #1
F1C = AxleCarriage(F1) #create an Anticipating Carriage mechanism adjacent to it
R1.define_mesh(REVERSE_PINION_DISTANCE, FP2.pinions) #when reversing pinions are in place
FC1.define_mesh(FC_DISTANCE, F1.digitstacks[0].wheels)
FC1.define_mesh(2*FC_DISTANCE, F1.digitstacks[0].wheels)
FC1.define_mesh(2*FC_DISTANCE, FP2.pinions)
FC1.define_mesh(FC_DISTANCE, R1.pinions) 
P31 = PinionStack("P31", NDIGITS) #pinions connecting from C to MP
P32 = PinionStack("P32", NDIGITS) #pinions connecting from C to FP
MP3 = PinionStack("MP3", NDIGITS) #movable long pinions to the right of C
FP3 = PinionStack("FP3", NDIGITS) #fixed long pinions to the right of C
P31.define_mesh(DIGITMESH_DISTANCE, C.digitstacks[0].wheels)
P31.define_mesh(-DIGITMESH_DISTANCE, C.digitstacks[1].wheels)
P31.define_mesh(ALWAYS, MP3.pinions) # connectors are always connected to the long pinions
MP3.define_mesh(0, FP3.pinions) # long pinions are normally always connected to each other 
MP3.define_mesh(LONGPINION_DISTANCE, FP3.pinions, shift=1) # but might be shifted up
P32.define_mesh(DIGITMESH_DISTANCE, C.digitstacks[0].wheels)
P32.define_mesh(-DIGITMESH_DISTANCE, C.digitstacks[1].wheels)
P32.define_mesh(ALWAYS, FP3.pinions) # connectors are always connected to the long pinions
R2 = PinionStack("R2", NDIGITS) #reversing pinions for F2
FC2 = PinionStack("FC2", NDIGITS) #connection pinions for F2
F2 = Axle("F2", 1, withcarry=True) #carriage #2
F2C = AxleCarriage(F2) #create an Anticipating Carriage mechanism adjacent to it
R2.define_mesh(REVERSE_PINION_DISTANCE, FP3.pinions) #when reversing pinions are in place
FC2.define_mesh(FC_DISTANCE, F2.digitstacks[0].wheels)
FC2.define_mesh(2*FC_DISTANCE, F2.digitstacks[0].wheels)
FC2.define_mesh(2*FC_DISTANCE, FP3.pinions)
FC2.define_mesh(FC_DISTANCE, R2.pinions) 
CTR = Counter("CTR")

#show some statistics
num_possible_meshes = 0
for pn in all_pinions_and_wheels:
   if pn.mesh_vposition: num_possible_meshes += len(pn.mesh_vposition)
print("\r")
print(f"configuration: {NDIGITS} digits in each of {len(all_axles)} digit stacks, {len(all_pinionstacks)} pinion stacks, {len(all_gears)} total gears, {num_possible_meshes} possible gear meshes")

#### define the studs we use for the multiplication/division barrels, and their semantics

def lift(barrel, axle_or_pinionstack, distance): #RAISE/LOWER: axle vertical motion
    if barrel.phase == 2: #do the liting
        axle_or_pinionstack.lift(distance)
        if type(axle_or_pinionstack) == Axle: #if it's an axle that goes through a digit wheel stack
            axle_or_pinionstack.driven = True # make it driven
    if barrel.phase == 13: #undo the lifting
        axle_or_pinionstack.lift(0)
        
def carry(barrel, carriage, direction): #ADD/SUB: compute and execute anticipating carriage
    if barrel.phase == 16: 
        carriage.compute_carriage(direction)
    if barrel.phase == 17:
        carriage.do_carriage(direction)
    if barrel.phase == 18:
        carriage.axle.digitstacks[0].doing_carries = False

def count1(barrel, axle:Axle, direction): #COUNT1: change a carriage axis by one without giving off to any other column
    if barrel.phase == 2:
        axle.digitstacks[0].count_by_1 = True #signal count mode
        axle.digitstacks[0].wheels[0].gear.direction = direction #CCW=decrement, CW=increment
        axle.driven = True

def counter_change(barrel, counter, direction): #increment or decrement a counter
    if barrel.phase == 4:
        add_to_advance_list(counter, direction)
        
def counter_clear(barrel, counter): #cleaer a counter
    if barrel.phase == 4:
        counter.clear()
       
def set_longcycle(barrel): #CYCLE20: specify this vertical as a long (20 time unit) cycle
    if barrel.phase == 2: barrel.num_phases = 20
    
def chk_runup(barrel, carriage:AxleCarriage, invert:bool): #IF_RUNUP: test for a "running up" condition after carriage
    #this might cause an extra +-1 turn of the reducing apparatus of the barrel
    if barrel.phase == 18:
        if (carriage.running_up ^ invert):
            barrel.doskip = True
            
def chk_sign(barrel, carriage:AxleCarriage, invert:bool): #IF_NEG/POS: test for result sign after carriage
    #this might cause an extra +-1 turn of the reducing apparatus of the barrel
    if barrel.phase == 18:
        if (carriage.digitstacks[0].wheels[NDIGITS].whposition & 1) ^ invert:
            barrel.doskip = True   
            
def dostop(barrel): #STOP
    global stopped
    if barrel.phase == 2: stopped = True
        
initialize_studs()   # F1 and F2 have carriage, so only one digit wheel in a cage
#studs commented out are not currently used by either barrel
create_stud("RAISE_MP1",     lambda barrel: lift(barrel, MP1, LONGPINION_DISTANCE))
create_stud("RAISE_MP2",     lambda barrel: lift(barrel, MP2, LONGPINION_DISTANCE))
create_stud("RAISE_MP3",     lambda barrel: lift(barrel, MP3, LONGPINION_DISTANCE))
create_stud("REVERSE_R1",    lambda barrel: lift(barrel, R1, REVERSE_PINION_DISTANCE))
create_stud("REVERSE_FC1",   lambda barrel: lift(barrel, FC1, FC_DISTANCE))
create_stud("MESH_FC1",      lambda barrel: lift(barrel, FC1, FC_DISTANCE*2))
create_stud("REVERSE_R2",    lambda barrel: lift(barrel, R2, REVERSE_PINION_DISTANCE))
create_stud("REVERSE_FC2",   lambda barrel: lift(barrel, FC2, FC_DISTANCE))
create_stud("MESH_FC2",      lambda barrel: lift(barrel, FC2, FC_DISTANCE*2))
create_stud("RAISE_P11",     lambda barrel: lift(barrel, P11, DIGITMESH_DISTANCE))
create_stud("LOWER_P11",     lambda barrel: lift(barrel, P11, -DIGITMESH_DISTANCE))
create_stud("LOWER_P12",     lambda barrel: lift(barrel, P12, -DIGITMESH_DISTANCE))
create_stud("RAISE_P12",     lambda barrel: lift(barrel, P12, DIGITMESH_DISTANCE))
create_stud("RAISE_P13",     lambda barrel: lift(barrel, P13, DIGITMESH_DISTANCE))
#create_stud("LOWER_P14",      lambda barrel: lift(barrel, P14, -DIGITMESH_DISTANCE))
create_stud("RAISE_P14",     lambda barrel: lift(barrel, P14, DIGITMESH_DISTANCE))
create_stud("RAISE_P21",     lambda barrel: lift(barrel, P21, DIGITMESH_DISTANCE))
create_stud("LOWER_P21",     lambda barrel: lift(barrel, P21, -DIGITMESH_DISTANCE))
create_stud("RAISE_P22",     lambda barrel: lift(barrel, P22, DIGITMESH_DISTANCE))
create_stud("LOWER_P22",     lambda barrel: lift(barrel, P22, -DIGITMESH_DISTANCE))
#create_stud("RAISE_P23",     lambda barrel: lift(barrel, P23, DIGITMESH_DISTANCE))
create_stud("LOWER_P23",     lambda barrel: lift(barrel, P23, -DIGITMESH_DISTANCE))
create_stud("RAISE_P24",     lambda barrel: lift(barrel, P24, DIGITMESH_DISTANCE))
#create_stud("LOWER_P24",     lambda barrel: lift(barrel, P24, -DIGITMESH_DISTANCE))
create_stud("RAISE_P31",     lambda barrel: lift(barrel, P31, DIGITMESH_DISTANCE))
create_stud("LOWER_P31",     lambda barrel: lift(barrel, P31, -DIGITMESH_DISTANCE))
create_stud("RAISE_P32",     lambda barrel: lift(barrel, P32, DIGITMESH_DISTANCE))
create_stud("LOWER_P32",     lambda barrel: lift(barrel, P32, -DIGITMESH_DISTANCE))
create_stud("RAISE_A",       lambda barrel: lift(barrel, A, DIGITFINGER_DISTANCE))
create_stud("LOWER_A",       lambda barrel: lift(barrel, A, -DIGITFINGER_DISTANCE))
create_stud("RAISE_B",       lambda barrel: lift(barrel, B, DIGITFINGER_DISTANCE))
create_stud("LOWER_B",       lambda barrel: lift(barrel, B, -DIGITMESH_DISTANCE))
create_stud("RAISE_C",       lambda barrel: lift(barrel, C, DIGITFINGER_DISTANCE))
create_stud("LOWER_C",       lambda barrel: lift(barrel, C, -DIGITMESH_DISTANCE))
create_stud("RAISE_F1",      lambda barrel: lift(barrel, F1, DIGITMESH_DISTANCE))
create_stud("RAISE_F2",      lambda barrel: lift(barrel, F2, DIGITMESH_DISTANCE))
create_stud("ADD_F1C",       lambda barrel: carry(barrel, F1C, CW))
create_stud("SUB_F1C",       lambda barrel: carry(barrel, F1C, CCW))
create_stud("ADD_F2C",       lambda barrel: carry(barrel, F2C, CW))
create_stud("SUB_F2C",       lambda barrel: carry(barrel, F2C, CCW))
create_stud("MINUS1F1",      lambda barrel: count1(barrel, F1, CCW))
create_stud("MINUS1F2",      lambda barrel: count1(barrel, F2, CCW))
create_stud("PLUS1F1",       lambda barrel: count1(barrel, F1, CW))
create_stud("PLUS1CTR",      lambda barrel: counter_change(barrel, CTR, CW))
create_stud("MINUS1CTR",     lambda barrel: counter_change(barrel, CTR, CCW))
create_stud("CLEARCTR",      lambda barrel: counter_clear(barrel, CTR))
create_stud("IF_RUNUP_F1",   lambda barrel: chk_runup(barrel, F1C, True), can_skip=True)
create_stud("IF_RUNUP_F2",   lambda barrel: chk_runup(barrel, F2C, True), can_skip=True)
create_stud("IF_NORUNUP_F1", lambda barrel: chk_runup(barrel, F1C, False), can_skip=True)
create_stud("IF_NORUNUP_F2", lambda barrel: chk_runup(barrel, F2C, False), can_skip=True)
create_stud("IF_RUNUP_CTR",  lambda barrel: chk_runup(barrel, CTR, True), can_skip=True)
create_stud("IF_NORUNUP_CTR",lambda barrel: chk_runup(barrel, CTR, False), can_skip=True)
#create_stud("IF_NEG_F1",     lambda barrel: chk_sign(barrel, F1, True), can_skip=True)
create_stud("CYCLE20",       lambda barrel: set_longcycle(barrel))
create_stud("STOP",          lambda barrel: dostop(barrel))

# barrel assembler "macros" that are sets of studs
#cages have x1 in upper, x2 in lower
A1_ADD_A2 = {RAISE_A, RAISE_P11, LOWER_P12}
A2_ADD_B1 = {LOWER_A, LOWER_P11, RAISE_P14}
A2_SHL_ADD_A1 = {LOWER_A, LOWER_P11, RAISE_MP1, RAISE_P12}
B1_ADD_B2 = {RAISE_B, RAISE_P22, LOWER_P21}
B1_ADD_A1 = {RAISE_B, RAISE_P13, RAISE_P12}
B1_SHR_ADD_C2 = {RAISE_B, RAISE_P22, RAISE_MP2, LOWER_P23}
B1_SHR_ADD_B2 = {RAISE_B, RAISE_P22, RAISE_MP2, LOWER_P21}
B1_ADD_F1 = {RAISE_B, RAISE_P22, REVERSE_R1, REVERSE_FC1, ADD_F1C, CYCLE20}
B1_SUB_F1 = {RAISE_B, RAISE_P22, MESH_FC1, SUB_F1C, CYCLE20}
B2_ADD_F1 = {LOWER_B, LOWER_P22, REVERSE_R1, REVERSE_FC1, ADD_F1C, CYCLE20}
B2_SUB_F1 = {LOWER_B, LOWER_P22, MESH_FC1, SUB_F1C, CYCLE20}
B2_ADD_B1 = {LOWER_B, LOWER_P22, RAISE_P21}
B2_SHR_ADD_B1 = {LOWER_B, LOWER_P22, RAISE_MP2, RAISE_P21}
C1_ADD_F2 = {RAISE_C, RAISE_P32, REVERSE_R2, REVERSE_FC2, ADD_F2C, CYCLE20}
C1_SUB_F2 = {RAISE_C, RAISE_P32, MESH_FC2, SUB_F2C, CYCLE20}
C1_ADD_C2 = {RAISE_C, RAISE_P32, LOWER_P31}
C1_SHL_ADD_C2 = {RAISE_C, RAISE_P31, RAISE_MP3, LOWER_P32}
C1_SHR_ADD_C2 = {RAISE_C, RAISE_P32, RAISE_MP3, LOWER_P31}
C2_SHL_ADD_C1 = {LOWER_C, LOWER_P31, RAISE_MP3, RAISE_P32}
C2_SHL_ADD_C1_left = {LOWER_C, LOWER_P23, RAISE_MP2, RAISE_P24}
C2_SHR_ADD_C1 = {LOWER_C, LOWER_P32, RAISE_MP3, RAISE_P31}
C2_SHL_SUB_F1 = {LOWER_C, LOWER_P23, RAISE_MP2, REVERSE_R1, REVERSE_FC1, SUB_F1C, CYCLE20}
C2_SUB_F2 = {LOWER_C, LOWER_P32, MESH_FC2, SUB_F2C, CYCLE20}
C2_SHL_ADD_B2 = {LOWER_C, LOWER_P23, RAISE_MP2, LOWER_P22}
C2_ADD_B2 = {LOWER_C, LOWER_P23, LOWER_P22}
C2_ADD_C1 = {LOWER_C, LOWER_P23, RAISE_P24}
C2_ADD_C1_right = {LOWER_C, LOWER_P32, RAISE_P31}
C2_ADD_F2 = {LOWER_C, LOWER_P32, REVERSE_R2, REVERSE_FC2, ADD_F2C, CYCLE20}
F1_ADD_B1 = {RAISE_F1, REVERSE_R1, REVERSE_FC1, RAISE_P22}
ZERO_A1 = {RAISE_A}
ZERO_A2 = {LOWER_A}
ZERO_B1 = {RAISE_B}
ZERO_B2 = {LOWER_B}
ZERO_C2 = {LOWER_C}
ZERO_F1 = {RAISE_F1}
ZERO_F2 = {RAISE_F2}
ZERO_CTR = {CLEARCTR}
DECR_F1 = {MINUS1F1, SUB_F1C, CYCLE20}
DECR_F2 = {MINUS1F2, SUB_F2C, CYCLE20}
INCR_F1 = {PLUS1F1, ADD_F1C, CYCLE20}

########  define the multiply and divide barrels  ########

''' multiply #3A, C1 x B1 to F2
*** like 3A, but optimize next digit transition to be always 5 cycles
*** only requires running-up detection, not zero detection
zero F2, F1, C2, B2 // one result, 3 temps, carriages F2,F1
outerloop: // multiplicand  in C1, multiplier in B1
  B1 -> shr+C2, shr+B2, +F1 // multiplier to F1, /10 to B2 and C2
  C2 -> shl-F1 // isolate lsd in F1
  --F1; if (F1<0) goto next1; else goto innerloop1 // skip innerloop if multiplier digit is 0
next1:  //(shifted) multiplicand in C1, remaining multiplier in B2, -1 in F1
  C1 -> shl +C2; B2 -> +F1, +B1; if (F1<0) goto stop else goto next1a
innerloop1: // shifted multiplicand in C1, multiplier digit in F1, product accumulating in F2
  C1 -> +F2, +C2; --F1;  if (F1>=0) goto innerloop2 else goto next2 // one cycle per addition!
next2a: // shifted multiplicand in C1, multiplier in B1
  F1 ->;  goto outerloop
stop: stop
next1a: // shifted multiplicand in C2, multiplier in B1
  F1 ->; C2 -> +C1; goto outerloop
innerloop2: // shifted multiplicand in C2, multiplier digit in F1, product accumulating in F2
  C2 -> +F2, +C1; --F1; if (F1>=0) goto innerloop1 else goto next1 // one cycle per addition!
next2:  // (shifted) multiplicand in C2, remaining multiplier in B2, -1 in F1
  C2 -> shl +C1;  B2 -> +F1, +B1;  if (F1<0) goto stop else goto next2a
 '''
mulpgm = program("multiply program", studnames) #create and assemble the program
mulpgm.vertical(              ZERO_F1, ZERO_F2, ZERO_B2, ZERO_C2)
mulpgm.vertical("outerloop",  B1_SHR_ADD_C2, B1_SHR_ADD_B2, B1_ADD_F1)
mulpgm.vertical(              C2_SHL_SUB_F1)
mulpgm.vertical(              DECR_F1, IF_RUNUP_F1, "next1")
mulpgm.vertical("next1",      C1_SHL_ADD_C2, B2_ADD_F1, B2_ADD_B1, IF_NORUNUP_F1, "stop")
mulpgm.vertical("innerloop1", C1_ADD_F2, C1_ADD_C2, DECR_F1, IF_NORUNUP_F1, "innerloop2")
mulpgm.vertical("next2a",     ZERO_F1, "outerloop")
mulpgm.vertical("stop",       STOP)
mulpgm.vertical("next1a",     ZERO_F1, C2_ADD_C1, "outerloop")
mulpgm.vertical("innerloop2", C2_ADD_F2, C2_ADD_C1, DECR_F1, IF_NORUNUP_F1, "innerloop1")
mulpgm.vertical("next2",       C2_SHL_ADD_C1, B2_ADD_F1, B2_ADD_B1, IF_NORUNUP_F1, "stop");
mulpgm.end_program()
mulpgm.disassemble()
mulpgm.showverticals()
BARMUL = Barrel("BARMUL", mulpgm) #create a barrel with that program on it

'''/*** divide #4, C2 / C1 to F1 rem F2
*** same as divide #3, but jumps conform to barrel limitations
zero F1, F2, A1, A2, B1, B2, CTR // 2 results, 3 temps, 1 counter, carriages F1,F2
   A1=1; C2 -> add F2
phase1: // adder=A1, divisor=C1, dividend=F2
   C1 -> sub F2, add C2; A1 -> add A2; if (F2 >= 0) goto phase1a; else goto phase2
phase1a:
   C2 -> add F2, shl (using F1 pinions!) add C1; A2 -> shl add A1; ++CTR; goto phase1; // restore dividend, shift divisor and adder
phase2: // adder=A2, divisor=C2, dividend-divisor in F2
   C2 -> add F2, add C1;  A2 -> add B1; // restore dividend in F2, divisor to C1, adder to B1
loop1: // divisor=C1, adder=B1
   C1 -> sub F2, add C2; B1 -> add F1, add B2; if (F2< 0) goto shift2; else goto loop2 // do subtraction, add to quotient
stop: goto done;
shift1: // divisor in C1, adder in B1
   C1 -> add F2, shr add C2; B1 -> sub F1, shr add B2; --CTR; if (CTR >=0) goto loop2; else goto done // do restores and shifts
loop1b: // divisor=C1, adder=B1
  C1 -> sub F2, add C2; B1 -> add F1, add B2; if (F2< 0) goto shift2; else goto loop2
shift2: // divisor in C2, adder in B2
  C2 -> add F2, shr add C1; B2 -> sub F1, shr add B1; -- CTR; if (CTR <0) goto stop; else goto loop1;// do restores and shifts
loop2: // divisor=C2, adder=B2
   C2 -> sub F2, add C1; B2 -> add F1, add B1; if (F2 >=0) goto loop1b;  else goto shift1;
done:'''
divpgm = program("divide program", studnames) #create and assemble the program
divpgm.vertical(              ZERO_F1, ZERO_F2, ZERO_A1, ZERO_A2, ZERO_B1, ZERO_B2, ZERO_CTR)
divpgm.vertical(              INCR_F1)
divpgm.vertical(              F1_ADD_B1)
divpgm.vertical(              B1_ADD_A1, C2_ADD_F2)
divpgm.vertical("phase1",     C1_SUB_F2, C1_ADD_C2, A1_ADD_A2, IF_NORUNUP_F2, "phase1a")
divpgm.vertical("phase1a",    C2_ADD_F2, C2_SHL_ADD_C1_left, A2_SHL_ADD_A1, PLUS1CTR, "phase1")
divpgm.vertical("phase2",     C2_ADD_F2, C2_ADD_C1_right, A2_ADD_B1)
divpgm.vertical("loop1",      C1_SUB_F2, C1_ADD_C2, B1_ADD_F1, B1_ADD_B2, IF_RUNUP_F2, "shift2")
divpgm.vertical("stop",       STOP)
divpgm.vertical("shift1",     C1_ADD_F2, C1_SHR_ADD_C2, B1_SUB_F1, B1_SHR_ADD_B2, MINUS1CTR, IF_NORUNUP_CTR, "loop2")
divpgm.vertical("loop1b",     C1_SUB_F2, C1_ADD_C2, B1_ADD_F1, B1_ADD_B2, IF_RUNUP_F2, "shift2" )
divpgm.vertical("shift2",     C2_ADD_F2, C2_SHR_ADD_C1, B2_SUB_F1, B2_SHR_ADD_B1, MINUS1CTR, IF_RUNUP_CTR, "stop")
divpgm.vertical("loop2",      C2_SUB_F2, C2_ADD_C1_right, B2_ADD_F1, B2_ADD_B1, IF_NORUNUP_F2, "loop1b")
divpgm.vertical("done",       STOP)
divpgm.end_program()
divpgm.disassemble()
divpgm.showverticals()
BARDIV = Barrel("BARDIV", divpgm) #create a barrel with that program on it

# test drivers

def domult(x, y, verbose=True): #multiply C1 x B1 and put the product in F2
    global stopped, timeunit, awaiting_advance, cycle
    BARMUL.reset(0) #reset the barrel to initial conditions
    C1._setvalue(x, print=False) #put the input operands on their axes
    B1._setvalue(y, print=False) 
    if verbose: print(f"multiplying {x} by {y}")
    stopped = False
    timeunit = 0
    cycle = 0
    awaiting_advance = []
    while not stopped: #until the barrel stops us
        add_to_advance_list(BARMUL, CCW) #start each time unit by advancing only the barrel state
        timeunit_tick() #process state changes until there are no more
    right = F2._value() == x*y
    if verbose or not right: 
        print(f"{cycle} cycles done in {timeunit} time units, or {timeunit*seconds_per_timeunit/60:.2f} minutes")  
        F2._printvalue()
        print(f"answer is {'correct' if right else 'WRONG!'}")
        print()
        
def dodiv(x, y, verbose=True): #divide c2/c1,  put the quotient in F1 and the remainder in F2
    global stopped, timeunit, awaiting_advance, cycle
    BARDIV.reset(0) #reset the barrel to initial conditions
    C2._setvalue(x, print=False) #put the input operands on their axes
    C1._setvalue(y, print=False) 
    if verbose: print(f"dividing {x} by {y}")
    stopped = False
    timeunit = 0
    cycle = 0
    awaiting_advance = []
    while not stopped: #until the barrel stops us
        add_to_advance_list(BARDIV, CCW) #start each time unit by advancing only the barrel state
        timeunit_tick() #process state changes until there are no more
    right = F1._value() == x//y and F2._value() == x % y
    if verbose or not right: 
        print(f"{cycle} cycles done in {timeunit} time units, or {timeunit*seconds_per_timeunit/60:.2f} minutes")  
        F1._printvalue()
        F2._printvalue()
        print(f"answer is {'correct' if right else 'WRONG!'}")
        print()   
 
#trace = TRACE_ALL #TRACE_BARRELS + TRACE_ENDING_VALUES #+ TRACE_WHEELS #+ TRACE_QUEUES
#timelimit = 500
print()
domult(12345,67)
dodiv(12345, 67)

import random
random.seed(1)
maxtest=10000000000
for _ in range(5):
    domult(random.randrange(0,maxtest), random.randrange(0,maxtest))
for _ in range(10):
    dodiv(random.randrange(0,maxtest), random.randrange(0,maxtest//1000))
    
#/*