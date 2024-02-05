'''
*******************************************************************************************************
 An assembler and simulator for the proposed instruction set architecture of the Analytical Engine
*******************************************************************************************************
 
--- Introduction ---

An AE program is created by writing a series of Python function calls that resemble 
traditional assembly-language statements, like these:
   
     add   (V1, V2, V3)       #add axis 1 to axis 2 and put the result on axis 3
     jmpz  (V4, "somewhere")  #if the value on axis 4 is zero, jump to "somewhere"
     
The result is an internally-generated loop of Operation Cards, and another of Variable Cards.
It can also generate a series of Number Cards for entering constants into the Store, but
they cannot be looped or repeated.

The program on the cards can be displayed for checking with the function "disassemble()".

The program can be run on a simulated engine with the function "run()". By default it generates
a trace of the relevant internal machine state as it executes, and then displays some statistics
when it stops.

Once we define the format of the cards, we can add a function that will draw (or even punch, 
given a connection to an appropriate device) the cards, which then can be stitched into 
loops and loaded onto the reading prisms of the engine.


--- the assembler language specification, by example ---

Dyadic instructions generate one operation card and three variable cards

    add (V1, V2, V3)      # V1+v2 --> V3
    sub (V1, V2, V3)      # normally operands are read destructively and become zero, but
    mul (V1.R, V2, V3)    #  appending ".R" makes the access non-destructive ("restoring access")
    div (V1, V2, [V3,V4]) # the destination can be a list of variable axes in the Store

Monadic instructions generate one operation card and two variable cards

    shl (V1, V2)          # shift V1 left one digit (multiply by 10) and put the result in V2
    shr (v1, V2)          # shift V1 right one digit (divide by 10) and put the result in V2

Jump instructions generate one operation card that contains a count and direction of operation cards to skip,
and one variable card that contains the count of variable cards to skip. In both cases the count is relative
to the card following the current one.

    jmp  (V1, "name")    # jump to label "name" (the value of axis V1 is ignored)
    jmpz (V1, "name")    # jump to label "name" if V1 is zero
    jmpn (V1, "name")    # jump to label "name" if V1 is negative (TBD: what about zero?)
    jmpp (V1, "name")    # jump to label "name" if V1 is positive (TBD: what about zero?)
    
The instruction to load a constant from the next Number Card into the location specified on a Variable Card

    num (V1, value)      # load the number card having the specified signed value

Miscellaneous instructions generate only one operation card

    stop ()              # stop the program and the engine

Assembler pseudo-operations and control assignments

    label("name")      # define a location at the next instruction to be the target of jumps
    initialize()       # clear the cards and zero all Store variables
    disassemble()      # show the generated operation and variable cards
    run()              # execute the cards to run the program
    showvariable("the answer", V7) # display a Store variable
    Trace = True       # enable the trace of operations during the run
    decimals = 6       # set the number of implied digits to the right of the decimal point

-------------------------------------------------------------------------------------------------------------------
 --- TODOs ---
  Better timing estimates, in particular for add/sub when sign has to be changed
  Refactor the source into separate files for assembler, simulator, and examples -- which Python makes hard!
  
 --- change log ---
 L. Shustek, 17 Sept 2023 and later: various simulator experiments
 L. Shustek, 25 Dec 2023, forked from the engine timing simulator and created the assembler/simulator
 L. Shustek, 13 Jan 2024, add Number Cards; add jmpp; show target labels in disassembly
 '''

'''************************************************************************************************************************
                     Analytical Engine user-level instruction assembler
***************************************************************************************************************************
 I really, really, wanted the AE program to look almost like assembly language. So I flout conventional wisdom
 about what is acceptable behavior in Python and dynamically create global variable names for the Store axes. Then they
 can be referred to as just V3 for a normal giving off (destructive readout), and V3.R for restoring (non-destructive) 
 readout. The result is simple uncluttered instructions like this: mul (V2, V2R, V3). The Pythonic way would be to
 use a dictionary, but then all the V references have to be ugly quoted strings. One minor downside to our approach
 is that IDEs like Visual Studio Code will decorate the Vn variables because they are undefined at compile time.
 '''
num_store_variables = 25
ADD,              SUB,  MUL,  DIV,  SHL,  SHR,  JMP,  JMPZ,  JMPN,  JMPP,  NUM,  STOP = 0,1,2,3,4,5,6,7,8,9,10,11
opnames = ["add","sub","mul","div","shl","shr","jmp","jmpz","jmpn","jmpp","num","stop"]
opvars  = [  3,    3,    3,    3,    2,    2,    1,    1,     1,      1,    1,     0] #of variable cards for each opcode

class var_axis_R: #the subclass that allows the ".R" notation for restoring variable access
    def __init__(self):
        self.rtype = True
class var_axis: #create one of these for each variable axis in the Store
    def __init__(self, name):
        self.name=name
        self.value=0
        self.rtype = False
        self.R = var_axis_R() #for V4.R type references
        self.R.parent = self
        self.R.name = name
def var_value(v): #return the value of an axis variable
    if v.rtype: #restoring-type variable access
        return v.parent.value #just return the current value
    else: #non-restoring ("giving off") variable access
        value = v.value #retrieve the current value
        v.value = 0 #leave it zeroed
        return value

class variable_card:
    def __init__(self, axes): #axes is a list of one or more Vn's
        global variable_cards
        variable_cards.append(self)
        self.axes = axes #all the axes specified on this variable card
        self.vcardndx = len(variable_cards)-1 #0 origin internal numbering of the variable cards

class operation_card:
    def __init__(self, op): #op is one of ADD, SUB, MUL, etc.
        global operation_cards
        operation_cards.append(self)
        self.op = op
        self.ocardndx = len(operation_cards)-1 #0 origin internal numbering of the operation cards
        
class number_card:
    def __init__(self, value):
        global number_cards
        number_cards.append(self)
        self.value = value
        self.ncardndx = len(number_cards)-1 #0 origin internal numbering of the operation cards
        
def result_card(z): #create a variable card to be used for operation results
    if not isinstance(z, list):
        z = [z] #make sure the result is a list of axes
    for var in z: 
        if var.rtype: error(f"result axis {var.parent.name} has .R")
    variable_card(z) #create result card, perhaps with multiple axes noted

def error(s):
    print(f"\nError: {s}")
    exit()

def op2(x, op, y, z): #create cards for a dyadic operator
    variable_card([x]) 
    operation_card(op)
    variable_card([y])
    result_card(z)
def add(x, y, z):
    op2(x, ADD, y, z)
def sub (x, y, z):
    op2(x, SUB, y, z)
def mul(x, y, z):
    op2(x, MUL, y, z)
def div (x, y, z):
    op2(x, DIV, y, z)
    
def op1(x, op, z): #create cards for a monatic operator
    variable_card([x])
    operation_card(op)
    result_card(z)
def shr(x, z):
    op1(x, SHR, z)
def shl(x, z):
    op1(x, SHL, z)

def num(x, value):  #create cards to load a constant number into the store
    number_card(value)
    operation_card(NUM)
    result_card(x)

def jmpgen(x, op, labelname): #create cards for a jump
    vcard = variable_card([x]) #create a variable card that contains an axis we might or
    #might not test, but in either case contains the skip distance for the variable card stack
    ocard = operation_card(op) #create the operation card that also contains the operation card skip distance and direction
    if labelname in labels: #it is a reference to an existing label 
        lab = labels[labelname]
        if lab.defined: #it is a backward reference to a previously defined label
            ocard.forward = False
            ocard.counter = ocard.ocardndx - lab.ocardndx + 1 #from next instruction
            vcard.counter = vcard.vcardndx - lab.vcardndx + 1 #from next variable
        else: #it is a forward reference to an as yet undefined label already created by an earlier forward reference
            ocard.forward = True
            lab.ocardrefs.add(ocard) #add both our cards to those awaiting the definition of the label
            lab.vcardrefs.add(vcard)
    else: #it is a forward reference to a never before seen undefined label 
        lab = labelrec(labelname) #create the undefined label 
        lab.defined = False
        ocard.forward = True
        lab.ocardrefs = {ocard} #we are the first jump instructure to await its definition
        lab.vcardrefs = {vcard}
        labels[labelname] = lab #add the label to the dictionary of labels
def jmp(x, labelname):
    jmpgen(x, JMP, labelname)
def jmpz(x, labelname):
    jmpgen(x, JMPZ, labelname)
def jmpn(x, labelname):
    jmpgen(x, JMPN, labelname)
def jmpp(x, labelname):
    jmpgen(x, JMPP, labelname)
    
class labelrec: #the information about a symbolic label
    def __init__(self, name):
        self.name = name
        self.vcardrefs = self.ocardrefs = {} #empty sets for cards awaiting the definition]
        #also: ocardndx, vcardndx, defined

def label(name): #create a label at the current location
    if name in labels: #the label record already exists from one or more earlier forward references
        lab = labels[name] #get that label record
        if lab.defined: error(f"duplicate label: {name}")
        lab.ocardndx = len(operation_cards) #record in the label the current position of both card stacks
        lab.vcardndx = len(variable_cards)
        lab.defined = True #now it has become defined
        for ocard in lab.ocardrefs: #update all the earlier jump operation cards that refer forward to this label
            ocard.counter = lab.ocardndx - ocard.ocardndx -1 #from next instruction
            ocard.forward = True #they must perforce all be forward jumps
        lab.ocardrefs = {}
        for vcard in lab.vcardrefs: #also update all the variable cards that refer forward to this label
            vcard.counter = lab.vcardndx - vcard.vcardndx - 1 #from next variable
        lab.vcardrefs  = {}
    else: #create a new defined label to which there are no forward references
        lab = labelrec(name) #create a new label record
        lab.ocardndx = len(operation_cards) #record in the label the current position of both card stacks
        lab.vcardndx = len(variable_cards)
        lab.defined = True
        labels[name] = lab #add it to the dictionary of labels

def stop(): #generate a stop instruction
    operation_card(STOP)
    
def decimal(n): #stringify a number that has an implied decimal point
    if decimals == 0:  return f'{n}'
    else:
        if n<0: 
            n=-n
            negative=True
        else: negative=False
        return f'{"-" if negative else ""}{n//10**decimals:1d}.{n%10**decimals:0{decimals}d}'

def checkcards():
    for labname in labels: #check for undefined labels
        lab = labels[labname]
        if len(lab.vcardrefs) + len(lab.ocardrefs) > 0: error(f"undefined label: {lab.name}")
    #what other checks could we do here?
    
def disassemble(): #disassemble the operation and variable cards into a pseudo-assembly language listing
    checkcards() #first check for errors
    print("\n                      program disassembly")
    print(  "---------------------------------------------------------------")
    labelfield = 12
    operationfield=35
    print(f'{"labels":<{labelfield}}{"operation cards":<{operationfield}}variable cards\n')
    opcardndx  = vcardndx = ncardndx = 0
    for ocard in operation_cards:
        label=False
        for labname in labels: #check labels at this location
            lab = labels[labname]
            if lab.ocardndx == ocard.ocardndx:
                if label: print() #another label for the same place: each on a line
                print(f"{lab.name}:{' ':{labelfield-len(lab.name)-1}}", end="")
                label=True
        if not label: print(f"{' ':{labelfield}}", end="")
        print(f"{opcardndx+1:3}: {opnames[ocard.op]}", end="")
        opfieldused = 3+2+len(opnames[ocard.op])
        targetmsg = " to "
        if ocard.op in {JMP, JMPN, JMPP, JMPZ}: #jumps are relative to the instruction after
            ocardtarget = 1 + (ocard.ocardndx+1) + (ocard.counter if ocard.forward else -ocard.counter)
            for labname in labels: #check for labels at the target location
                lab = labels[labname] 
                if lab.ocardndx+1 == ocardtarget:
                    targetmsg += f"{lab.name}, "
            targetmsg += f"op card {ocardtarget}"
            opfieldused += len(targetmsg)
            print(targetmsg, end="")
        for i in range(opvars[ocard.op]): #for each variable card this operation card uses
            if vcardndx >= len(variable_cards): error ("missing variable cards")
            print(f"{vcardndx+1:>{operationfield-opfieldused+3}}: ", end="")
            vcard = variable_cards[vcardndx]
            for axis in vcard.axes:
                print(axis.name, end="")
                if axis.rtype: print(".R", end="")
                print(" ", end="")
            vcardndx += 1
            if ocard.op in {JMP, JMPN, JMPP, JMPZ}:
                vcardtarget = 1 + (vcard.vcardndx+1) + (vcard.counter if ocard.forward else -vcard.counter)
                print(f" jump to var card {vcardtarget}", end="")
            if ocard.op == NUM: 
                if ncardndx >= len(variable_cards): error ("missing number card")
                print(f" from num card {ncardndx+1:}: ", end="")
                value = number_cards[ncardndx].value
                ncardndx += 1
                print(f"{decimal(value)}", end="")
            print()
            opfieldused = -labelfield
        opcardndx += 1 #simulate advancing the program counter
    if vcardndx < len(variable_cards): error ("extra variable cards")
    print()
 
variables = [] #create all the axes and the variables naming them
for i in range(num_store_variables): 
     axis = var_axis(f"V{i}")
     variables.append(axis)
     globals()[f"V{i}"] = axis

'''******************************************************************************************************
                     Analytical Engine user-level instruction simulator
*********************************************************************************************************'''
seconds_per_unit = .157
units_per_cycle = 20
minutes_per_cycle = seconds_per_unit * units_per_cycle / 60.
Trace = True #generate an execution trace?

def initialize(title): #reset the engine
    global variable_cards, operation_cards, number_cards, cum_cycles, instruction_count, labels, variables
    variable_cards = [] #empty lists for the cards
    operation_cards = [] 
    number_cards = []
    labels = {} #empty dictionary of jump target labels
    for axis in variables: axis.value = 0 #all variable axes are zeroed
    cum_cycles = 0
    instruction_count = 0
    if Trace: print(f"\n\n**** engine initialized for {title} ****")
    
def do_multiply(multiplicand, multiplier, use_table=True):
    setup_cycles = 0
    sign = 1
    if multiplicand < 0:
        multiplicand = -multiplicand
        sign = -1
        setup_cycles += 1
    if multiplier < 0:
        multiplier = -multiplier
        sign *= -1
        setup_cycles += 1
    if multiplicand < multiplier: #make multiplier smaller
        multiplicand, multiplier = multiplier, multiplicand #how does the engine do this?
    multiplier_size = len(str(multiplier))
    if use_table: setup_cycles += 1+9 #number of cycles to create the table
    else: setup_cycles += 1
    product = 0
    multiply_cycles = 0 #cycles for the multiplication proper, without setup
    for loop in range(multiplier_size):
        next_digit = multiplier % 10
        multiply_cycles += 1 #one cycle for choosing the table entry, testing for zero, and shifting
        if next_digit > 0: #skip zero multiplier digits
            product += next_digit*multiplicand * 10**loop 
            if use_table:
                multiply_cycles += 1 #cycles for adding the single table entry
            else:
                multiply_cycles += 1*next_digit #cycles for adding the multiplicand next_digit times
        else: multiply_cycles += 1 #even zero takes two cycles
        multiplier //= 10
    product = sign * (product // 10**decimals) #need to do this incrementally, at no cycle cost
    return {"product":product, "total_cycles":setup_cycles + multiply_cycles, "digit_cycles":multiply_cycles/(multiplier_size)}

def do_divide(dividend, divisor, use_table=True, selector_digits=2):
    if divisor == 0:
        return {"quotient":0, "remainder":0, "total_cycles":0, "digit_cycles":0}
    sign = 1
    if dividend < 0:
        dividend = -dividend
        sign = -1
    if divisor < 0:
        divisor = -divisor
        sign *= -1
    #if dividend < divisor:  #not correct when decimals>0
    #    return {"quotient":0, "remainder":dividend, "total_cycles":2, "digit_cycles":0}
    #shift the divisor left so it lines up with the dividend
    divisor_size = len(str(divisor)) + 1 #include leading 0
    dividend_size = len(str(dividend)) + 1 # include leading 0
    shift_distance = dividend_size - divisor_size
    setup_cycles = 2 + shift_distance  #1 cycle per shift plus overhead to determine sizes?
    if use_table: setup_cycles += 9  #cycles to make the table (no overlap with shifts?)
    quotient = 0 #get ready to do the division
    divide_cycles = 0 #cycles for the division proper, without setup
    #the number of positions for trial subtractions is one more than the difference 
    #between the number of significant digits in the dividend and the divisor
    for loop in range(shift_distance+1+decimals):
        quotient *= 10
        if use_table:
            dividend_topn = dividend // (10**(dividend_size-selector_digits)) #top n digits of the current dividend
            if dividend_topn >= 10**selector_digits: print(f"ERROR: dividend topn too big for {selector_digits} digits: {dividend_topn}")
            divide_cycles += 1 #one cycle for selecting the table axis?
            for multiple_number in range(1,10): #find the multiple whose top n digits are no larger than the dividend's
                trial_multiple = divisor * multiple_number 
                trial_multiple_topn = trial_multiple // 10**(divisor_size-selector_digits)
                if trial_multiple_topn > dividend_topn: 
                    if multiple_number > 1: multiple_number -= 1 #always at least subtract the first table entry
                    break;
            multiple = divisor * multiple_number * 10**(shift_distance-loop)
            dividend -= multiple #subtract the chosen multiple
            quotient += multiple_number #increment the quotient
            divide_cycles += 1 #cycles to subtract chosen table axis
        else: #no table: repeated subtraction until underflow
            while (dividend > 0):
                dividend -= divisor * 10**(shift_distance-loop)
                quotient += 1
                divide_cycles += 1 #cycles for each subtraction
        while dividend < 0: #we subtracted too much
            # This happens at most once with no table, or for 2-digit table selection when the 2 digits match.
            # It could happen more than once for 1-digit table selection.
            dividend += divisor * 10**(shift_distance-loop) #add back the divisor
            quotient -= 1
            divide_cycles += 1 #cycles for each correction cycle
        #step down the divisor and all the table axes
        dividend_size -= 1
        if not use_table: divide_cycles += 1 #time for shift
        #shifting takes no time when using a table because it can be overlapped with selection?
    return {"quotient":quotient, "remainder":dividend*sign, "total_cycles":setup_cycles + divide_cycles, 
            "digit_cycles":divide_cycles/(shift_distance+1+decimals)}

def divide(dividend, divisor, show=False, use_table=True, selector_digits=2):
    answer = do_divide(dividend, divisor, use_table, selector_digits)
    wrong = answer["quotient"]*divisor + answer["remainder"] != dividend \
        or answer["remainder"] > divisor or answer["remainder"] < 0
    if wrong: print ("WRONG ANSWER:")
    if wrong or show: 
       print(f'{dividend} / {divisor} = {answer["quotient"]} remainder {answer["remainder"]}'
             f' in {answer["total_cycles"]} time units and {answer["digit_cycles"]:.2f} per digit')
    return answer

def multiply(multiplicand, multiplier, show=False, use_table=True):
    answer = do_multiply(multiplicand, multiplier, use_table)
    wrong = answer["product"] != multiplicand * multiplier
    if wrong: print ("WRONG ANSWER:")
    if wrong or show: 
       print(f'{multiplicand} * {multiplier} = {answer["product"]}'
             f' in {answer["total_cycles"]} time units and {answer["digit_cycles"]:.2f} per digit')
    return answer

def run(): #execute the program
    checkcards()
    global cum_cycles, instruction_count
    varcard_ndx = opcard_ndx = numcard_ndx = 0
    vcard = 0
    print(f"---- starting the program with {len(operation_cards)} operation cards and {len(variable_cards)} variable cards")

    def var(): #get the value of the axis specified on a variable card
        nonlocal varcard_ndx, vcard
        vcard = variable_cards[varcard_ndx]
        varcard_ndx += 1
        if varcard_ndx >= len(variable_cards): varcard_ndx = 0
        axis = vcard.axes[0]
        value = var_value(axis) 
        if Trace: print(f" {axis.name}={decimal(value)} ", end="" )
        return value
    
    def jump(forward, opskip, varskip): #jump forward or backwards, skipping both operation and variable cards
        global cum_cycles
        nonlocal varcard_ndx, opcard_ndx
        if forward:
            opcard_ndx += opskip
            while opcard_ndx >= len(operation_cards): opcard_ndx -= len(operation_cards)
            varcard_ndx += varskip
            while varcard_ndx >= len(variable_cards): varcard_ndx -= len(variable_cards)
            if Trace: print(f" jump forward to op card {opcard_ndx+1} and var card {varcard_ndx+1}", end="")
        else:
            opcard_ndx -= opskip
            while opcard_ndx < 0: opcard_ndx += len(operation_cards)
            varcard_ndx -= varskip
            while varcard_ndx <0: varcard_ndx += len(variable_cards)
            if Trace: print(f" jump backward to op card {opcard_ndx+1} and var card {varcard_ndx+1}", end="")
        if opskip > varskip: cum_cycles += opskip
        else: cum_cycles += varskip

    while True: #loop until a "stop" instruction is executed
        opcard = operation_cards[opcard_ndx]
        op = opcard.op
        instruction_count += 1
        if Trace: print(f"{opcard_ndx+1:2d}: {opnames[op]:4} ", end="")
        opcard_ndx += 1 #move the operation card stack to the next card
        if opcard_ndx >= len(operation_cards): opcard_ndx = 0 #they're in a loop
        if op == ADD: 
            result = var()+var()
            cum_cycles += 1
        if op == SUB: 
            result = var()-var()
            cum_cycles += 1
        if op == MUL: 
            answer = do_multiply(var(), var(), use_table=tables)
            result = int(answer["product"])
            cum_cycles += answer["total_cycles"]
        if op == DIV: 
            answer = do_divide(var(), var(), use_table=tables)
            result = int(answer["quotient"])
            cum_cycles += answer["total_cycles"]
        if op == SHL:
            result = var() * 10
            cum_cycles += 1
        if op == SHR:
            result = var() // 10
            cum_cycles += 1
        if op == NUM:
            if numcard_ndx >= len(variable_cards): error("ran out of Number Cards")
            ncard = number_cards[numcard_ndx]
            numcard_ndx += 1
            if Trace: print(f" N{numcard_ndx}", end="")
            result = ncard.value
            cum_cycles += 2 #is this right?
        if op == JMP:
            var() #read the variable card to get the vcard skip count and direction
            jump(opcard.forward, opcard.counter, vcard.counter)
        if op == JMPZ:
            if (var() == 0):
               jump(opcard.forward, opcard.counter, vcard.counter)
            elif Trace: print(" jump not taken", end="")
        if op == JMPN:
            if (var() < 0):
                jump(opcard.forward, opcard.counter, vcard.counter)
            elif Trace: print(" jump not taken", end="")
        if op == JMPP:
            if (var() > 0):
                jump(opcard.forward, opcard.counter, vcard.counter)
            elif Trace: print(" jump not taken", end="")
        if op == STOP:
            print()
            break
        if op not in {JMP, JMPZ, JMPN, JMPP}: #it is an opcode that stores a result
            if Trace: print(f" = {decimal(result)} to", end="")
            result_card = variable_cards[varcard_ndx] #read the result variable card
            varcard_ndx += 1
            for axis in result_card.axes: #assign to all axes on the result variable card
                if axis.value != 0: error(f"assignment to non-zero axis {axis.name}")
                if Trace: print(f" {axis.name}", end="")
                axis.value = result
        if Trace: print()
    print()
    showtiming()

def showvariable(number, answer):
    print(f'{number} is {decimal(answer.value)}')

def showtiming():
    print(f'{instruction_count} instructions were executed in {cum_cycles*minutes_per_cycle:.1f} minutes,\
 using {decimals} fraction decimals, {"with" if tables else "without"} tables ')


'''*********************************************************************************************************
                Analytical Engine user-level instruction program examples
************************************************************************************************************'''
'''-------------------------------------------------------
        Compute N Fibonacci numbers
---------------------------------------------------------'''
initialize("calculation of Fibonacci numbers")
tables = False
decimals=0
howmany = 10

num    (V2, 1)          #constant
num    (V3, howmany)    #how many numbers to compute
num    (V4, 0)          #previous Fibonacci number
num    (V5, 1)          #current Fibonacci number
sub    (V7, V3, V7)     # put -count in V7 as loop counter
label  ("loop")
add    (V4, V5.R, V6)   #compute next number
add    (V5, V4, V4)     #move current to previous
add    (V6, V5, V5)     #move next to current
add    (V7, V2.R, V7)   #increment loop counter
jmpn   (V7.R, "loop")   #jump if not done
stop()

disassemble()
run()
showvariable(f"The last of {howmany} Fibonacci numbers", V5)

'''-------------------------------------------------------------------------------
  Compute the Greatest Common Divisor of two integers using Euclid's algorithm
        def gcd(a, b):
            while a != b:
                if a > b: a = a - b
                else: b = b - a
            return a
----------------------------------------------------------------------------------'''
initialize("calculation of GCD")
decimals = 0
a=27
b=6
V1.value = a 
V2.value = b

#compute the GCD of V1 and V2 using Euclid's algorithm
label ("loop")
sub   (V1.R, V2.R, V3) #compare a to b
jmpz  (V3.R, "end")
jmpn  (V3,"b_GT_a" )
sub   (V1, V2.R, V1)   #a=a-b
jmp   (V3, "loop")
label ("b_GT_a")
sub   (V2, V1.R, V2)   #b=b-a
jmp   (V3, "loop")
label ("end")
stop  ()

disassemble()
run()
showvariable(f"The GCD of {a} and {b}", V1)

'''-------------------------------------------------------------------------------------------
  The Lovelace calculation of B7,
  with or without tables, and for any number of digits to the right of the decimal point
----------------------------------------------------------------------------------------------'''
def compute_B7():
    initialize("computation of Bernoulli B7")
    global decimals, table
    table=False
    decimals=6
    scalefactor = 10**decimals
    
#initial Store variable values come from Number Cards that contain constants
    num (V1, 1 * scalefactor)            #constant 1
    num (V2, 2 * scalefactor)            #constant 2
    num (V3, 4 * scalefactor)            #n=4, to compute the 4th number, B(2n-1), or B7
    num (V21, int(1/6 * scalefactor))    #B1  previously computed Bernoulli number
    num (V22, -int(1/30 * scalefactor))  #B3  previously computed Bernoulli number
    num (V23, int(1/42 * scalefactor))   #B5  previously computed Bernoulli number
#program: computes B7 = -A0 - A1B1 - A3B3 - A5B5
    mul (V2.R,  V3.R, [V4,V5,V6])   #step 1: 2n
    sub (V4,    V1.R,  V4)          #step 2: 2n-1
    add (V5,    V1.R,  V5)          #step 3: 2n+1
    div (V4,    V5,    V11)         #step 4: (2n-1)/(2n+1)
    div (V11,   V2.R,  V11)         #step 5: (1/2)((2n-1)/(2n+1))
    sub (V13,   V11,   V13)         #step 6: -(1/2)((2n-1)/(2n+1)) = A0
    sub (V3.R,  V1.R,  V10)         #step 7: n-1  counter=3
    add (V2.R,  V7,    V7)          #step 8: 2    copy constant
    div (V6.R,  V7.R,  V11)         #step 9: 2n/2 = A1
    mul (V21.R, V11.R, V12)         #step 10: A1*B1
    add (V12,   V13,   V13)         #step 11: A0+A1*B1
    sub (V10,   V1.R,  V10)         #step 12: n-2  counter=2
    sub (V6,    V1.R,  V6)          #step 13: 2n-1
    add (V1.R,  V7,    V7)          #step 14: 2+1 = 3
    div (V6.R,  V7.R,  V8)          #step 15: (2n-1)/3
    mul (V8,    V11,   V11)         #step 16: (2n/2)*((2n-1)/3)
    sub (V6,    V1.R,  V6)          #step 17: 2n-2
    add (V1.R,  V7,    V7)          #step 18: 3+1 = 4
    div (V6.R,  V7.R,  V9)          #step 19: (2n-2)/4
    mul (V9,    V11,   V11)         #step 20: (2n-2)*((2n-1)/3)*((2n-2)/4) = A3
    mul (V22.R, V11.R, V12)         #step 21: A3*B3
    add (V12,   V13,   V13)         #step 22: A0+A1*B1+A3*B3
    sub (V10,   V1.R,  V10)         #step 23: n-3   counter= 1
    sub (V6,    V1.R,  V6)          #step 13: 2n-1
    add (V1.R,  V7,    V7)          #step 14: 2+1 = 3
    div (V6.R,  V7.R,  V8)          #step 15: (2n-1)/3
    mul (V8,    V11,   V11)         #step 16: (2n/2)*((2n-1)/3)
    sub (V6,    V1.R,  V6)          #step 17: 2n-2
    add (V1.R,  V7,    V7)          #step 18: 3+1 = 4
    div (V6,    V7,    V9)          #step 19: (2n-2)/4
    mul (V9,    V11,   V11)         #step 20: (2n-2)*((2n-1)/3)*((2n-2)/4)= A3
    mul (V23.R, V11,   V12)         #step 21: A3*B3
    add (V12,   V13,   V13)         #step 22: A0+A1*B1+A3*B3
    sub (V10,   V1.R,  V10)         #step 23: n-4   counter = 0
    add (V13,   V24,   V24)         #step 24: A0+A1*B1+A3*B3+A5*B5 = B7
    add (V1.R,  V3,    V3)          #step 25: n=5  ready to compute B9!
    stop ()

    disassemble()
    run()
    showvariable("B7", V24)
compute_B7()
exit()
