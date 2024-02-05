A component-level simulator for the small Babbage Analytical Engine
-------------------------------------------------------------------

The engine is simulated at a resolution of basic "time units", 15 or 20 of which comprise a "cycle" of the engine. 
The activities during a cycle are controlled by the current "verticals" on the microprogram barrels, each of which can be thought of as microprogram instruction word.

The model is of an interconnected assembly of hierarchical "components" that have internal state. 

Examples of components are:
   -	digit wheels
   -	stacks of digit wheels
   -	axles that go through one or more interleaved stacks of digit wheels
   -	anticipating carriage for an axle
   -	barrels, and the studs on barrels
   
Components are created  with simple Python function calls:
    A =  Axle("A",2)  #a simple axle with 2 digits per cage
    B =  Axle("B",2, withcarry=True) #an axle with anticipating carriage
    
Barrel studs are defined, and given semantics that describe their effect on the engine, using calls like these:

   create_stud("GIVE_G_TO_C",   lambda barrel: mesh(barrel, G, C))
   create_stud("SHR_C_TO_D",    lambda barrel: mesh(barrel, C, D, shift=-1)) 
   create_stud("ADD_A_TO_B",    lambda barrel: mesh(barrel, A, B))
   create_stud("SUB_F_FROM_E",  lambda barrel: mesh(barrel, F, E, subtract=True))
   
The “microprogram” on the barrels is then specified by a series of function calls that resemble traditional assembly-language statements with optional labels.
The output is a matrix that indicates where on the cylindrical barrel the studs need to be placed. 
Here is an example program fragment that does unsigned multiplication:

   mulpgm = program("multiply program", studnames) #create and assemble the program
   mulpgm.vertical("outerloop",  SHR_C_TO_D, GIVE_C_TO_E)
   mulpgm.vertical(              SHL_D_TO_F, GIVE_D_TO_G)
   mulpgm.vertical(              SUB_F_FROM_E, GIVE_A_TO_D, CYCLE20) 
   mulpgm.vertical("innerloop",  GIVE_D_TO_A, DECR_E, CYCLE20, IF_RUNUP_EC,  "doadd")
   mulpgm.vertical("doadd",      ADD_A_TO_B, GIVE_A_TO_D, CYCLE20,  "innerloop")
   mulpgm.vertical(              SHL_A_TO_D)
   mulpgm.vertical(      GIVE_D_TO_A, ADD_G_TO_E, GIVE_G_TO_C, CYCLE20, IF_NORUNUP_EC,  "zero_e")
   mulpgm.vertical("zero_e",     ZERO_E,  "outerloop")
   
The simulated execution can produce various levels of diagnostic tracing information, or just the results at the end:
   multiplying 123456 by 123456
   done in 1547 time units, or 4.05 minutes
   product is 15241383936 

For more information see the comment blocks at the start of the source code files.
