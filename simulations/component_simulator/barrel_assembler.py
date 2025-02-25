'''file: barrel_assembler.py

    *******  AN ASSEMBLER FOR ANALYTICAL ENGINE BARREL MICROPROGRAMS  *********

An AE microprogram is created by writing a series of Python function calls that resemble
traditional assembly-language statements. The output is a matrix that indicates where
on the cylindrical barrel the studs need to be placed. 

Each microprogram word is a vertical column of studs that control function in the engine. 
During each cycle of 15 or 20 time units, the cylinder can rotate from 1 to 8 positions 
(1+2+4, plus one more as a conditional) to the word that will control the next cycle.

We care where the "verticals" around the cylinder are placed, since the limitation on 
the jump distance is a significant constraint on the program that we need to model.

We do not care about where the studs are located vertically since that will depend on the arrangement
of the rods, levers, and platforms that effect the control that the studs represent. By default we
locate the studs on the barrel in the order they are defined symbolically with calls to create_stud. 

The program is defined with a series of calls to vertical(), which takes a variable number of 
arguments in three sections:

- The first optional argument is a quoted string representing a symbolic label we are defining
  at the location of this vertical, which can be the target of jumps.
  
- The next arguments are the names of the studs that are to be "on". If a stud isn't named, it is
  programmed to be "off". (We don't currently implement the feature where neither stud is present,
  indicating "same as before", but we could.) The stud names and their semantics are defined using
  the "create_stud" function in the simulator module; see there for details.
  
- The last optional argument is a quoted string that is the name of a symbolic label, and it
  generates a jump to the vertical at that label. If any stud in this vertical is defined to
  be a conditional test, and if the condition is satisfied, the jump will be to the vertical
  one further away. If there is no jump specified, the default is a jump to the following instruction.
  
The assembler will complain about missing or duplicate labels, and about jump distances greater than 7.

Here is an example program that does unsigned multiplication:

    mulpgm = program("multiply program", studnames)
    mulpgm.vertical( "outerloop",  SHR_C_TO_D, GIVE_C_TO_E)
    mulpgm.vertical(               SHL_D_TO_F, GIVE_D_TO_G)
    mulpgm.vertical(               SUB_F_FROM_E, GIVE_A_TO_D, CYCLE20) 
    mulpgm.vertical( "innerloop",  GIVE_D_TO_A, DECR_E, CYCLE20, IF_RUNUP_EC, "doadd")
    mulpgm.vertical( "doadd",      ADD_A_TO_B, GIVE_A_TO_D, CYCLE20, "innerloop")
    mulpgm.vertical(               SHL_A_TO_D)
    mulpgm.vertical(               GIVE_D_TO_A, ADD_G_TO_E, GIVE_G_TO_C, CYCLE20, IF_NORUNUP_EC, "zero_e")
    mulpgm.vertical( "zero_e",     ZERO_E, "outerloop")
    mulpgm.vertical(               STOP)
    mulpgm.end_program()

A call to mulpgm.disassemble() will generate this, where the studs are in numerical order:

------ disassembly of multiply program ------
   label   vert      studs                                            --> jumps to
 outerloop   0  GIVE_C_TO_E, SHR_C_TO_D
             1  GIVE_D_TO_G, SHL_D_TO_F
             2  GIVE_A_TO_D, SUB_F_FROM_E, CYCLE20
 innerloop   3  GIVE_D_TO_A, DECR_E, IF_RUNUP_EC, CYCLE20             --> doadd or doadd+1
     doadd   4  GIVE_A_TO_D, ADD_A_TO_B, CYCLE20                      --> innerloop
             5  SHL_A_TO_D
             6  GIVE_D_TO_A, GIVE_G_TO_C, ADD_G_TO_E, IF_NORUNUP_EC, CYCLE20 --> zero_e or zero_e+1
    zero_e   7  ZERO_E                                                --> outerloop
             8  STOP

A call to mulpgm.showverticals() will generate this:

------  layout of studs on the multiply program barrel ------
stud                        0    1    2    3    4    5    6    7    8
41           STOP  OFF _____*____*____*____*____*____*____*____*_______
40                 ON  _____________________________________________*__
39        CYCLE20  OFF _____*____*___________________*_________*____*__
38                 ON  _______________*____*____*_________*____________
37  IF_NORUNUP_EC  OFF _____*____*____*____*____*____*_________*____*__
36                 ON  ___________________________________*____________
35    IF_RUNUP_EC  OFF _____*____*____*_________*____*____*____*____*__
34                 ON  ____________________*___________________________
33         ZERO_E  OFF _____*____*____*____*____*____*____*_________*__
32                 ON  ________________________________________*_______
31         DECR_E  OFF _____*____*____*_________*____*____*____*____*__
30                 ON  ____________________*___________________________
29   SUB_F_FROM_E  OFF _____*____*_________*____*____*____*____*____*__
28                 ON  _______________*________________________________
27     ADD_G_TO_E  OFF _____*____*____*____*____*____*_________*____*__
26                 ON  ___________________________________*____________
25     ADD_A_TO_B  OFF _____*____*____*____*_________*____*____*____*__
24                 ON  _________________________*______________________
23     SHL_A_TO_D  OFF _____*____*____*____*____*_________*____*____*__
22                 ON  ______________________________*_________________
21     SHL_D_TO_F  OFF _____*_________*____*____*____*____*____*____*__
20                 ON  __________*_____________________________________
19     SHR_C_TO_D  OFF __________*____*____*____*____*____*____*____*__
18                 ON  _____*__________________________________________
17    GIVE_G_TO_C  OFF _____*____*____*____*____*____*_________*____*__
16                 ON  ___________________________________*____________
15    GIVE_D_TO_A  OFF _____*____*____*_________*____*_________*____*__
14                 ON  ____________________*______________*____________
13    GIVE_A_TO_D  OFF _____*____*_________*_________*____*____*____*__
12                 ON  _______________*_________*______________________
11    GIVE_D_TO_G  OFF _____*_________*____*____*____*____*____*____*__
10                 ON  __________*_____________________________________
 9    GIVE_C_TO_E  OFF __________*____*____*____*____*____*____*____*__
 8                 ON  _____*__________________________________________
 7       MOVEBACK  OFF _____*____*____*____*_________*____*_________*__
 6                 ON  _________________________*______________*_______
 5          MOVE4  OFF _____*____*____*____*____*____*____*_________*__
 4                 ON  ________________________________________*_______
 3          MOVE2  OFF _____*____*____*____*____*____*____*_________*__
 2                 ON  ________________________________________*_______
 1          MOVE1  OFF ________________________________________________
 0                 ON  _____*____*____*____*____*____*____*____*____*__
'''

STUDON = 0 #bottom stud of a pair: the control is engaged
STUDOFF = 1 #top stud of a pair: the control is not engaged

def asmerror(msg:str): #a fatal error in the program being assembled
   print("Error: ", msg)
   exit()

studnum_moves = 0
def jumpstud(name, number): #for MOVE1, MOVE2, MOVE4, and MOVEBACK
    global studnum_moves
    globals()[name] = number  #create a global for this module that is the number of the stud ON position
    studnum_moves = number+2
    
class labelrec: #the information about a symbolic label
   def __init__(self, name):
      self.name = name
      self.vrefs = {} #empty set for verticals awaiting the definition
      self.defined = None #is it defined?
      self.vndx = None #where it is defined to be

class program: #a program for one barrel
    def __init__(self, name, studnames):
        self.name = name
        self.labels = {} #empty dictionary of jump targets labelname:labelrec
        self.verticals = [] #where the program will go
        self.skip_verticals = [] #which verticals are eligible to cause a +-1 extra jump
        self.studnames = studnames #the names of all the studs, each one twice

    def label(self, name): #create a label at the current location
        here = len(self.verticals)
        if name in self.labels: #the label already exists from one or more earlier forward references
            lab = self.labels[name] #get that label record
            if lab.defined: asmerror(f"duplicate label: {name}")
            lab.vndx = here #record the location of the label
            lab.defined = True #now it has become defined
            for vertndx in lab.vrefs: #update all the earlier jumps that refer forward to this label
                jumpstuds = jmpgen(here-vertndx, vertndx) #create the jump studs
                for stud in jumpstuds: self.verticals[vertndx].append(stud) #and add them to the vertical
            lab.vrefs = {}
        else: #create a new defined label for which there are no forward references
           if here in [*self.labels.values()]: asmerror(f"redundant label: {name}") #only one label per vertical
           lab = labelrec(name) #create a new label record
           lab.vndx = here #record where it is
           lab.defined = True
           self.labels[name] = lab #add it to the dictionary of labels
    
    def goto(self, labelname):
        here = len(self.verticals) #the vertical we are about to define
        if labelname in self.labels: #it is a reference to an existing label
            lab = self.labels[labelname]
            if lab.defined: #it is a backward reference to a previously defined label
                return jmpgen(lab.vndx-here, here)
            else: #it is a forward reference to an as yet undefined label already created by an earlier forward reference
               lab.vrefs.add(here) #add us to the set of verticals awaiting the definition of the label
        else: #it is a forward reference to a never before seen undefined label 
            lab = labelrec(labelname) #create the undefined label
            lab.defined = False
            lab.vrefs = {here} #we are the first vertical to await its definition
            self.labels[labelname] = lab #add the label to the dictionary of labels
        return []
    
    def vertical(self, *argv): #define one vertical with explicit studs
        studnumlist = [] #the list of STUDON stud numbers we want on in this vertical
        for arg in argv:
            if type(arg) == str: 
               if len(studnumlist)>0 : #if it is not at the start it is a jump to a label
                  jumpstuds = self.goto(arg) #generate the jump studs
                  for stud in jumpstuds: studnumlist.append(stud) #and add them to our vertical
               else: self.label(arg)  #it is a label definition
            else: #stud, or list of studs
                if (type(arg) != set):
                    arg = {arg} #convert stud to a set
                for stud in arg:
                    if not stud.studnum in studnumlist: #ignore attempts to add duplicates
                        studnumlist.append(stud.studnum) #add this stud's number to the vertical
                        if stud.can_skip: #if this stud can cause a skip
                            self.skip_verticals.append(len(self.verticals)) #note that this vertical can skip
        self.verticals.append(studnumlist) #add our list of stud numbers as a new vertical for this barrel program
    
    def end_program(self): #do post-processing of the program
        for labname in self.labels: #check for undefined labels
           lab = self.labels[labname]
           if len(lab.vrefs) > 0: asmerror(f"undefined label \"{lab.name}\"")
        for vertnum in range(len(self.verticals)): #Process each vertical
             vert = self.verticals[vertnum]
             #If no move studs are specified in this vertical, add "jump to next vertical"
             if all(stud >= studnum_moves for stud in vert):
                 self.verticals[vertnum].append(MOVE1+STUDON)
             #Add stud.OFF studs for any not specified.
             #(This will need to change if we implement no studs to mean "same as before".)
             for studnum in range(0, len(self.studnames), 2):
                if studnum == 114:
                    pass
                if not studnum in vert and not studnum+1 in vert: #neither OR nor OFF specified
                    self.verticals[vertnum].append(studnum+STUDOFF)
             self.verticals[vertnum] = sorted(self.verticals[vertnum]) #finally, sort by stud number
    
    def disassemble(self): #disassemble a barrel program
       print(f"\n------ disassembly of {self.name} ------")
       maxstudwidth = 80
       namewidth = 1
       if self.labels: namewidth +=  max(len(labname) for labname in self.labels)
       print(f'{"label   vert":>{namewidth+5}}{"      studs":{maxstudwidth}}--> jumps to')
       for vertnum in range(len(self.verticals)):
          vert = self.verticals[vertnum]
          label = " "
          for labname in self.labels: #see if there is a label here
              if self.labels[labname].vndx == vertnum: label = labname
          print(f"{label:>{namewidth}} {vertnum:3}  ", end="")
          studwidth = 0
          did_one = False
          for stud in vert: #show any "on" studs other than moves
            if stud >= studnum_moves and stud%2 == STUDON: 
                if did_one > 0: print(", ", end="")
                if studwidth > maxstudwidth-14: # too long: break to another line
                    print() 
                    print(f"{' ':>{namewidth+6}}", end="")
                    studwidth = 0
                print(f"{self.studnames[stud]}", end="")
                did_one = True
                studwidth += len(self.studnames[stud]) + 2
          #recreate the jump instruction if it's not an unconditional move to the next instruction
          if vert[0:studnum_moves//2] != [MOVE1, MOVE2+STUDOFF, MOVE4+STUDOFF, MOVEBACK+STUDOFF] or vertnum in self.skip_verticals:
              distance = 1*(vert[0]==MOVE1)+2*(vert[1]==MOVE2)+4*(vert[2]==MOVE4)
              if vert[3] == MOVEBACK: distance = -distance
              target = vertnum + distance 
              targetname=str(target)
              for name, lab in self.labels.items():
                  if lab.vndx == target: targetname=name
              if vertnum in self.skip_verticals: #show both destinations if this could be a skip
                   targetname += " or "+targetname
                   if MOVEBACK+STUDOFF in vert:
                       targetname += "+1"
                       target += 1
                   else:
                        targetname += "-1"
                        target -= 1
                   for name, lab in self.labels.items():
                       if lab.vndx == target: 
                           targetname += " (" + name + ")"
              if studwidth < maxstudwidth: #space out to the jump area
                  print(f'{" ":{maxstudwidth-studwidth}}', end="")
              print(f" --> {targetname}", end="")
          print()

    def showverticals(self): #show the verticals as they are arranged on the barrel
        print(f"\n------  layout of studs on the {self.name} barrel ------")
        namewidth = 1 + max(len(self.studnames[studnum]) for studnum in range(len(self.studnames)))
        print(f'{"stud":{namewidth+11}}', end="")
        for vert in range(len(self.verticals)):
            print(f"{vert:5}", end="")
        print()
        for studnum in range(len(self.studnames)-1, -1, -1):
            used = False
            print(f"{studnum:3} {self.studnames[studnum] if studnum%2==STUDOFF else ' '*namewidth:>{namewidth}} ", end="")
            print(f'{" ON " if studnum%2==STUDON else " OFF"} ___', end="")
            for vert in range(len(self.verticals)):
                stud_present = self.verticals[vert][studnum//2] == studnum+STUDON
                print(f'{"__*__" if stud_present else "_____"}', end="")
                used |= stud_present
            if studnum%2==STUDON and not used: print("unused", end="")
            print()
       
def jmpgen(n:int, here:int): #generate the stud ON list for a jump of n positions forward or backwards
   studnumlist = []
   if n < 0:
      studnumlist.append(MOVEBACK + STUDON)
      n = -n
   if n > 7: asmerror(f"Barrel jump greater than 7 at vertical {here}")
   if n > 3:
      studnumlist.append(MOVE4 + STUDON)
      n -= 4
   if n > 1:
      studnumlist.append(MOVE2 + STUDON)
      n -= 2
   if n > 0:
      studnumlist.append(MOVE1 + STUDON)
   return studnumlist
