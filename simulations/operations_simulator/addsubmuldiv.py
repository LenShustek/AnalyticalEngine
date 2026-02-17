#file: addsubmuldiv.py
'''**************************************************************************************************************
    Analytical Engine arithmetic operation state machine simulator
    
    This models the simplified Plan 27 engine, which contains three Mill registers (A, B, and C) with both
    top (A1, B1, C1) and bottom (A2, B2, C2) numbers, two sets of decade shifters, and two anticipating 
    carraiges (F1 and F2) that can do addition and subtraction.
    
    We simulate the signed "small operations" of addition and subtraction, including chained operations that 
    compute an accumuated total from multiple variables before transmitting the result to the Store. 
    In Babbage's terminology each variable fetched has an "accidental sign" (its sign in the Store), and
    an "algebraic sign" (whether to add or subtract it to the running total). He notated a sequence of
    operations like this:  +- (+-P) +- (+-Q) +- (+-R)
       
    We also simulate the signed "great operations" of multiplication and division, but without using
    the precomputed tables that Babbage proposed. That means we will often -- but not always! -- take more 
    cycles that Babbage would have.

    Among other things, this is an experiment to see if we can simplify the sign handling hardware.
    Following Babbage, the Store contains numbers in sign-magnitude format, with the N+1st "digit" being an 
    indication of the sign: even for positive, odd for negative.
    
    Here's the unusual part: The proposed Mill does 10's complement arithmetic, as Babbage proposed, but it 
    needs almost no hardware to deal with signs. For the small operations, the current sign of the value being 
    accumulated is recorded in the state of the microcode barrel. The state is changed based on the "running up" 
    of the accumulated value when addition or subtraction happens. For the great operations, the sign of the 
    result is simply determined by the parity of the sum of the signs of the operands.
    
    The only hardware for handling signs is therefore:
      - one wheel that records the sign of variables read from the Store, which is used in the Reducing Apparatus
        to choose the next barrel instruction so that the sign is recorded in the barrel state
      - one wheel (perhaps the same one) that can be set by a barrel stud to determine the sign to be written
        to the Store
    
    For the small operations, The barrel seems to need only a total of 14 "verticals" representing microinstructions. 
    That said, it remains to be seen how easy it is to implement the sometimes 4-way branches that determine the next 
    state. Barrel programming is very constrained.
    
    The  operation cards for this simulator are "add", "sub", "mul", "div", "writeback", and "stop". 
    The "writeback" operation terminates the chaining operations and transmits the result to the Store. 
    (Babbage separated those two functions so that intermediate results of a chained operation could be stored.
    If that turns out to be useful, we could do that too by using some other indication to end the chaining.)
    
    Unlike in Babbage's Plan 27, we do not expect the rack to be restored in the same cycle as the Store read or write 
    occurs. In all cases the cycle following a Store cycle doesn't use the store, so that's when the restoring happens. 
    As a result, our throughput for chained small operations is half Babbage's: 2 cycles per operation instead of 1.
    
    The rack restoration is not modeled here, but it is straightforward and can easily implement read access that is
    both destructive ("Zero Supply-cards" in Lovelace's terminology) and non-destructive ("Retaining Supply-cards").
    The only difference is whether the originating digit wheels are engaged when the rack is restored.
    
    Overflow is not handled here; it simply aborts the simulator. Even Babbage was not clear on what should be done. 
    We will need to make sure that the machine (a) signals the operator, and (b) is not left in a deranged non-
    restartable state. 
    
    L. Shustek, 7/24/2025
    L. Shustek, 2/16/2026  Update the comments; change "giveoff" to "writeback". 
*****************************************************************************************************************'''
import time

toobig = 100000000 #simulate only 8 digit arithmetic; change as desired

def storeval(location):
    return store_values[location] if store_signs[location]%2==0 else -store_values[location]
    
def dumpmem():
    for i in range(len(store_values)):
        print(f"  loc {i} is {storeval(i)}")
    
def do_test(test):
    global operation_cards, variable_cards, store_values, store_signs
    global next_operation_card, next_variable_card 
    global F1, F2, A1,A2, B1,B2, C1,C2, Signwheel, answers
    A1 = A2 = B1 = B2 = C1 = C2 = Signwheel = F1 = F2 = 0
    [operation_cards, variable_cards, store_values, store_signs, answers] = test
    next_operation_card = next_variable_card = 0
    cycles = run_state_machine()
    for answerset in answers:
        [location, answer] = answerset
        result = storeval(location)
        print(f"after {cycles} cycles the result {result} at location {location} is {'correct' if result == answer else 'INCORRECT'}")
        if result != answer: dumpmem()
 
def error(code, msg=""):
    print(f"*** error {code} {msg}")
    exit(0)
    
def read_operation_card():
    global operation, next_operation_card
    operation = operation_cards[next_operation_card]
    if trace_ops: print("operation:", operation)
    next_operation_card =(next_operation_card + 1) % len(operation_cards)

def read_variable_card():
    global variable, next_variable_card
    variable = variable_cards[next_variable_card]
    next_variable_card =(next_variable_card + 1) % len(variable_cards)

def store_to_B1():
    global B1, Signwheel
    B1 += store_values[variable]; #non-destructive read! store_values[variable] = 0
    Signwheel += store_signs[variable]; #non-destructive read! store_signs[variable] = 0
    if trace_mem: print(f"  read to B1 {'+' if Signwheel%2==0 else '-'}{B1} from store location {variable}")
    
def store_to_C1():
    global C1, Signwheel
    C1 += store_values[variable]; #non-destructive read! store_values[variable] = 0
    Signwheel += store_signs[variable]; #non-destructive read! store_signs[variable] = 0
    if trace_mem: print(f"  read to C1 {'+' if Signwheel%2==0 else '-'}{C1} from store location {variable}")
    
def store_to_C2():
    global C2, Signwheel
    C2 += store_values[variable]; #non-destructive read! store_values[variable] = 0
    Signwheel += store_signs[variable]; #non-destructive read! store_signs[variable] = 0
    if trace_mem: print(f"  read to C2 {'+' if Signwheel%2==0 else '-'}{C2} from store location {variable}")
    
def B1_to_store():
    global B1, Signwheel
    store_values[variable] += B1; B1 = 0
    store_signs[variable] += Signwheel; Signwheel = 0
    if trace_mem: print(f"  wrote from B1 {'+' if store_signs[variable]%2==0 else '-'}{store_values[variable]} to store location {variable}")

def B2_to_store():
    global B2, Signwheel
    store_values[variable] += B2; B2 = 0
    store_signs[variable] += Signwheel; Signwheel = 0
    if trace_mem: print(f"  wrote from B2 {'+' if store_signs[variable]%2==0 else '-'}{store_values[variable]} to store location {variable}")
    
def C1_to_store():
    global C1, Signwheel
    store_values[variable] += C1; C1 = 0
    store_signs[variable] += Signwheel; Signwheel = 0
    if trace_mem: print(f"  wrote from C1 {'+' if store_signs[variable]%2==0 else '-'}{store_values[variable]} to store location {variable}")
    
def decrement(wheel):
    return wheel-1

def increment(wheel):
    return wheel+1
 
def run_mul_state_machine():   
    global ncycles, trace_state
    global B1, B2, C1, C2, F1, F2
    mstate = "read mcand"
    state=None; del state #avoid typos
    #trace_state = trace_mem = True #TEMP
    #the first variable card has already been read
    while True:
        if trace_state: print(f'  at mstate "{mstate}"  F1={F1}  B1={B1} C1={C1}')
        ncycles += 1
        match mstate:
            case "read mcand":
                store_to_B1(); read_variable_card(); mstate = "read mply"
            case "read mply":
                store_to_C1(); mstate = "outerloop" 
            case "outerloop":
                C2+=int(B1/10); B2+=int(B1/10); F1+=B1; B1=0; mstate = "outerloop 2"
            case "outerloop 2":
                F1-=C2*10; C2=0; mstate = "outerloop 3"
            case "outerloop 3":
                F1-=1; mstate = "next1" if F1<0 else "innerloop1"
            case "next1":
                C2+=C1*10; C1=0; F1+=B2; B1+=B2; B2=0; mstate = "done" if F1<0 else "next1a"
            case "innerloop1":
                F2+=C1; C2+=C1; C1=0; F1=F1-1; mstate = "innerloop2" if F1>=0 else "next2"
            case "next2a":
                F1=0; mstate = "outerloop"
            case "done":
                #MUST SHIFT F2 RIGHT BY #DIGITS TO RIGHT OF DECIMAL PLACE
                B1+=F2; F2=0; read_variable_card()
                mstate = "write B1" 
            case "write B1":
                B1_to_store()
                return
            case "next1a":
                F1=0; C1+=C2; C2=0; mstate = "outerloop"
            case "innerloop2":
                F2+=C2; C1+=C2; C2=0; F1=F1-1; mstate = "innerloop1" if F1>=0 else "next1"
            case "next2":
                C1+=C2*10; C2=0; F1+=B2; B1+=B2; B2=0; mstate = "done" if F1<0 else "next2a"
            case _:
               error("bad mstate", mstate)   
  
def run_div_state_machine():
    global ncycles, trace_state, trace_mem
    global A1, A2, B1, B2, C1, C2, F1, F2, CTR
    dstate="read dividend"
    CTR=0
    #trace_state = trace_mem = True #TEMP
    #the first variable card has already been read
    while True:
        if trace_state: print(f'  at dstate "{dstate}"  F1={F1} F2={F2} A1={A1} A2={A2} B1={B1} B2={B2} C1={C1} C2={C2} CTR={CTR}'); time.sleep(1)
        ncycles += 1
        match dstate:  
            case "read dividend":
                store_to_C2(); read_variable_card(); A1=B1=F1=0; dstate="read divisor"
            case "read divisor":
                store_to_C1(); A2=B2=F2=CTR=0;  dstate="setup" #will do C2/C1 = F1 remainder F2
            case "setup":
                A1=increment(A1); F2+=C2; C2=0; dstate="phase1"
            #how can we check for divide by zero without having check-for-zero hardware in the carriage?
            #I can't see a place where checking for running-up will do it...  
            case "phase1": #preshift divisor (and adder) left until larger than dividend
                F2-=C1; C2+=C1; C1=0; A2+=A1; A1=0; dstate = "phase1a" if F2>=0 else "phase2" #trial subtraction
            case "phase1a":
                F2+=C2; C1+=C2*10; C2=0;  A1+=A2*10; A2=0; CTR=increment(CTR); dstate="phase1" #restore dividend; shift divisor and adder
            case "phase2": #adder=A2, divisor=C2, dividend-divisor in F2
                F2+=C2; C1+=C2; C2=0;  B1+=A2; A2=0; dstate="loop1" #restore dividend in F2, divisor to C1, adder to B1
            case "loop1":
                F2-=C1; C2+=C1; C1=0; F1+=B1; B2+=B1; B1=0; dstate = "shift2" if F2<0 else "loop2" #do subtraction, add to quotien
            case "shift1":
                F2+=C1; C2+=int(C1/10); C1=0; F1-=B1; B2+=int(B1/10); B1=0; CTR=decrement(CTR); dstate = "loop2" if CTR>=0 else "done C1B1 zero" #do restores and shifts
            case "loop1b":
                F2-=C1; C2+=C1; C1=0; F1+=B1; B2+=B1; B1=0; dstate = "shift2" if F2<0 else "loop2" #do subtraction, add to quotient
            case "shift2":
                F2+=C2; C1+=int(C2/10); C2=0; F1-=B2; B1+=int(B2/10); B2=0; CTR=decrement(CTR); dstate = "done C2B2 zero" if CTR<0 else "loop1"
            case "loop2":
                F2-=C2; C1+=C2; C2=0; F1+=B2; B1+=B2; B2=0; dstate = "loop1b" if F2>=0 else "shift1"
            case "done C1B1 zero":
                B1+=F1; F1=0; read_variable_card(); dstate="store quotient B1"
            case "store quotient B1":
                #MUST SHIFT B1 LEFT BY #DIGITS TO THE RIGHT OF THE DECIMAL POINT 
                B1_to_store(); C1+=F2; F2=0; read_variable_card(); dstate="store remainder" #store quotient, stage remainder CAN READ VAR CARD WHILE STORING??
            case "store remainder":
                C1_to_store() #store remainder
                return
            case "done C2B2 zero":
                B2+=F1; F1=0; read_variable_card(); C1=0; dstate="store quotient B2"
            case "store quotient B2":
                #MUST SHIFT B2 LEFT BY #DIGITS TO THE RIGHT OF THE DECIMAL POINT 
                B2_to_store(); C1+=F2; F2=0; read_variable_card(); dstate="store remainder"
            case _:
                error("bad dstate", dstate)
                
                
def run_state_machine():
    global F1, B1, Signwheel, ncycles
    state = "read first cards"
    ncycles = 0
    while True:
        if trace_state: print(f'  at state "{state}"  F1={F1}  B1={B1}')
        ncycles += 1
        match state:
            case "read first cards": 
                read_operation_card(); read_variable_card()
                if operation == "add": state = "read store, add, F1+"
                elif operation == "sub": state = "read store, sub, F1+"
                elif operation == "mul": run_mul_state_machine()
                elif operation == "div": run_div_state_machine()
                elif operation == "stop": break
                else: error("bad first op", operation)
            case "read store, add, F1+":
                store_to_B1(); state = "do add, F1+" if Signwheel%2 == 0 else "do sub, F1+"
            case "read store, sub, F1+":
                store_to_B1(); state = "do sub, F1+" if Signwheel%2 == 0 else "do add, F1+"
            case "read store, add, F1-":
                store_to_B1(); state = "do sub, F1-" if Signwheel%2 == 0 else "do add, F1-"
            case "read store, sub, F1-":
                store_to_B1(); state = "do add, F1-" if Signwheel%2 == 0 else "do sub, F1-"
            case "do add, F1+":
                F1+=B1; B1=0; Signwheel=0; read_operation_card(); read_variable_card() 
                if F1>=toobig: error("overflow")
                if operation == "add": state = "read store, add, F1+"
                elif operation == "sub": state = "read store, sub, F1+" 
                elif operation == "writeback": state = "FtoB1, F1+"
                else: error("bad op", operation)
            case "do sub, F1-":
                F1-=B1; B1=0; Signwheel=0;  read_operation_card(); read_variable_card()
                if F1<0: error("overflow")
                if operation == "add": state = "read store, sub, F1-"
                elif operation == "sub": state = "read store, add, F1-" 
                elif operation == "writeback": state = "FtoB1, F1-"
                else: error("bad op", operation)
            case "do sub, F1+":
                F1-=B1; B1=0; Signwheel=0; read_operation_card(); read_variable_card()
                if F1<0: #running up: F1 became negative
                    F1+=toobig #(not a real operation)
                    if operation == "add": state = "read store, sub, F1-"
                    elif operation == "sub": state = "read store, add, F1-" 
                    elif operation == "writeback": state = "FtoB1, F1-"
                    else: error("bad op", operation)
                else:
                    if operation == "add": state = "read store, add, F1+"
                    elif operation == "sub": state = "read store, sub, F1+" 
                    elif operation == "writeback": state = "FtoB1, F1+"
                    else: error("bad op", operation)
            case "do add, F1-":
                F1+=B1; B1=0; Signwheel=0; read_operation_card(); read_variable_card()
                if F1>=toobig: #running up: F1 became positive
                    F1-=toobig #(not a real operation)
                    if operation == "add": state = "read store, add, F1+"
                    elif operation == "sub": state = "read store, sub, F1+" 
                    elif operation == "writeback": state = "FtoB1, F1+"
                    else: error("bad op", operation)
                else:
                    if operation == "add": state = "read store, sub, F1-"
                    elif operation == "sub": state = "read store, add, F1-" 
                    elif operation == "writeback": state = "FtoB1, F1-"
                    else: error("bad op", operation)
            case "FtoB1, F1+":
                B1=F1; F1=0; Signwheel=0
                state = "write B1"
            case "write B1":
                B1_to_store()
                state = "read first cards"
            case "FtoB1, F1-":
                B1=F1; F1=0; Signwheel=0
                state = "complement F1"
            case "complement F1":
                F1-=B1; B1=0; 
                if F1<0: F1+=toobig #(not a real operation)
                state = "FtoB1 again"
            case "FtoB1 again":
                B1=F1; F1=0; Signwheel=1 #was just zeroed, so engage finger and move one position
                state = "write B1"
            case _:
                error("bad state", state)
    return ncycles
                
tests = [ #each test is: operations, variables, store values, store signs, answers
 
    #test all non-overflow binary operation cases
   [["add","add","writeback","stop"], [0,1,2], [10,11,0], [0,0,0],  [[2,21]]], #case 1   
   [["add","sub","writeback","stop"], [0,1,2], [10, 9,0], [0,0,0],   [[2,1]]], #case 3
   [["add","sub","writeback","stop"], [0,1,2], [10,11,0], [0,0,0],  [[2,-1]]], #case 4
   [["sub","sub","writeback","stop"], [0,1,2], [10,11,0], [0,1,0],   [[2,1]]], #case 5
   [["sub","add","writeback","stop"], [0,1,2], [10,12,0], [0,0,0],   [[2,2]]], #case 6
   [["add","sub","writeback","stop"], [0,1,2], [10,11,0], [1,0,0], [[2,-21]]], #case 7
   
   [["add","add","writeback","stop"], [0,1,2], [4, 5, 0], [1,1,0], [[2, -9]]], #two negatives in a row

   #test some chained cases
   [["add","add","add","writeback","stop"], [0,1,2,3], [10,11,12,0], [0,0,0,0 ], [[3,33]]], # ++10++11++12 = +33
   [["add","sub","sub","writeback","stop"], [0,1,2,3], [10,11,12,0], [0,0,0,0 ], [[3,-13]]], # ++10-+11-+12 = -13
   [["add","sub","sub","writeback","stop"], [0,1,2,3], [10,11,12,0], [1,1,0,0 ], [[3,-11]]], # +-10--11-+12 = -11
   
   #test a sequential operation that uses the result of a previous calculation
   [["add","add","writeback", "add","add","writeback","stop"], [0,1,2,2,3,4], [10,11,0,13,0], [0,0,0,0,0], [[4,34]]], #v0+v1->v2, v2+v3->v4

   #a few cycles of Fibonacci number computation
   [["add","add","writeback","add","add","writeback","add","add","writeback","stop"], [0,1,2,1,2,3,2,3,4,0],[8,13,0,0,0,0,0,0,0,0], [0]*10, [[4,55]]],
   
   #try all combinations of signs for multiplication
   [["mul", "stop"], [0,1,2], [123,456,0], [0,0,0], [[2,56088]] ],
   [["mul", "stop"], [0,1,2], [123,456,0], [1,0,0], [[2,-56088]] ],
   [["mul", "stop"], [0,1,2], [123,456,0], [0,1,0], [[2,-56088]] ],
   [["mul", "stop"], [0,1,2], [123,456,0], [1,1,0], [[2,56088]] ],
   
   #try all combinations of signs for division
   [["div","stop"], [0,1,2,3], [23,5,0,0], [0,0,0,0], [[2,4],[3,3]]],
   [["div","stop"], [0,1,2,3], [23,5,0,0], [1,0,0,0], [[2,-4],[3,3]]],
   [["div","stop"], [0,1,2,3], [23,5,0,0], [0,1,0,0], [[2,-4],[3,3]]],
   [["div","stop"], [0,1,2,3], [23,5,0,0], [1,1,0,0], [[2,4],[3,3]]],
   
   #some random division tests
   [["div","stop"], [0,1,2,3], [5,1,0,0], [0,0,0,0], [[2,5],[3,0]]],
   [["div","stop"], [0,1,2,3], [123456,123,0,0], [0,0,0,0], [[2,1003],[3,87]]],
   [["div","stop"], [0,1,2,3], [1234567,124,0,0], [0,0,0,0], [[2,9956],[3,23]]],



   []]

trace_state = False
trace_mem = False
trace_ops = False
testnum=1
for test in tests:
    if test: 
        print(f"*** test {testnum}")
        do_test(test)
        testnum += 1
    