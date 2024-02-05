An instruction-level simulator for the small Babbage Analytical Engine
----------------------------------------------------------------------

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
    
    