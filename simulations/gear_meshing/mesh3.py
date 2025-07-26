'''----------------------------------------------------------------------------------
This is a program to analyze 3 linked gears and use a Monte-Carlo technique to
perturb the axle locations so that the gears mesh correctly. We use it in the Plan 27 
design to find sizes and positions that mesh for the following loop of 3 gears:

 - the FC pinion (called I by Babbage) which links the fixed long pinion's 
   outer gear to the anticipating carriage gear wheel 
   
 - the RP reversing pinion (I1 by Babbage) that can optionally be
   inserted to change from addtion to subtraction
   
 - the FP fixed long pinion (L by Babage), whose position and orientation
   when at a digit position has already been determined by our more
   complex 3-group 5-gear loop analysis program.
 
Since FP to RP to FC is a 3-gear loop, it can't mesh continuously, but
only at gear-tooth increments. So in order to get the placement right, the
angle of FP for this analysis has to be such that all the *other* gear loops 
in all 3 groups of the Plan 27 layout are meshed and are at a digit position. 

During operation, vertical motion of FC and RP creates either the chain 
FP to RP to FC, or the chain FP to FC (and FP to RP idling). Although the 3-gear
loop is never meshed, the wheel position and rotations must be such that the
mesh can change whenever FP is at a digit position. 

A 3-gear loop is hard to make mesh, and it depends critically on the 
number of teeth. Unlike the 5-gear analysis program, this program tweaks
the number of teeth on the gear in addition to their positions in order
to disover configurations that work.

L. Shustek, 7/10/2025
-------------------------------------------------------------------------------------'''
import math, copy, time, datetime
from mesh_routines_1 import *

def show_result(kind:str, FPangle, angle, discrep, teeth, posn):
    print(f"{kind} mesh at FPangle {FPangle:.2f}, RPangle {angle:4.1f} deg: discrep {discrep:.3f} teeth {','.join(str(x) for x in teeth)} dia {', '.join(f'{teeth[i]/DP[i]:.2f}' for i in range(3))} pos {','.join(f'[{posn[i][0]:.6f},{posn[i][1]:.6f}] ' for i in range(3))} ")
    
def analyze_loops(name:str, FCright = True):   
    print(f"\r\r\nThree gear analysis of {name}")  
    if type(FP_angles) is list:
        [FP_angle, FP_angle_end, FP_angle_incr] = FP_angles
        FP_angle_steps = int((FP_angle_end-FP_angle)/FP_angle_incr)
    else:
        [FP_angle, FP_angle_steps, FP_angle_incr] = [FP_angles, 1, 0]
        
    for _ in range(FP_angle_steps):
       best = 99 #show the best result for each FP starting angle
   
       for RPteeth in RP_tooth_range: #choose the number of teeth in RP
            for FCteeth in FC_tooth_range: #choose the number of teeth in FC
                teeth = [FP_teeth, RPteeth, FCteeth]
                diams = [t/dp for t,dp in zip(teeth,DP)]
                #print("diameters:", diams, ", teeth:", teeth)
                FPtoRP = (diams[0]+diams[1])/2.0
                RPtoFC = (diams[1]+diams[2])/2.0
                FCtoFP = (diams[2]+diams[0])/2.0          
                [RP_angle, RP_angle_end, RP_angle_incr] = RP_angles
                RP_angle_steps = int((RP_angle_end-RP_angle)/RP_angle_incr)
                pass
                for _ in range(0, RP_angle_steps): #increment the counter-clockwise angle of FP to RP from the vertical
                    #compute the center positions of RP and FC
                    RPy = FPy-math.cos(math.radians(abs(RP_angle))) * FPtoRP
                    if RP_angle > 0: 
                        RPx  = FPx+math.sin(math.radians(abs(RP_angle))) * FPtoRP
                    else:
                        RPx  = FPx-math.sin(math.radians(abs(RP_angle))) * FPtoRP
                    leftright = 10.0 if FCright else -10.0
                    [FCx,FCy] = set_by_distance([FPx,FPy],FCtoFP, [RPx,RPy],RPtoFC, [FPx+leftright,FPy+leftright]) #FC is determined, but choose left or right version
                    positions = [[FPx,FPy], [RPx,RPy], [FCx,FCy]]
                    #print("new coords are: ", [[x[0],x[1]] for x in positions])
                    message, discrep, pitch_discrep, angles = verify_gear_tooth_alignment_angular("RP", 3, positions, teeth, DP, DP, initial_angle=FP_angle, verbose=False)
                    #print(f'angle {RP_angle} discrep is {discrep}, positions {[f"[{x[0]:.6f}],[{x[1]:.6f}]" for x in positions]}')
                    if discrep < threshold:
                        show_result("good", FP_angle, RP_angle, discrep, teeth, positions)
                    if discrep < best:
                        best = discrep
                        bestpos = copy.deepcopy(positions)
                        bestteeth = copy.deepcopy(teeth)
                        bestangle = RP_angle
                    RP_angle += RP_angle_incr
       show_result("BEST", FP_angle, bestangle, best, bestteeth, bestpos)
       FP_angle += FP_angle_incr

     #end of analyze_loops

print("\r")
if True: #my design    
    names = ["FP", "RP", "FC"]
    DP = [5, 5, 5]
    threshold = 1.0 #degrees how far off a "good" mesh can be
    FP_teeth = 16
    RP_tooth_range = range(7,10)
    FC_tooth_range = range(16,22)
    RP_angles = [-40.0, 0., 1.0]
    
    #The positions and orientation of the FPs are a a result of the 5-gear 3-group analysis,
    #and are written to c:\temp\FPconfig.txt and copied here.
    [FP2x,FP2y] = [0.38257152737429767,-2.9835710311223025]
    FP2_angle = 111.8229
    [FP3x,FP3y] = [8.750727598609839,-2.9807328724316635]
    FP3_angle = 159.0516
    
    [FPx,FPy] = [FP2x,FP2y] #where FP2 is 
    FP_angles = FP2_angle  #what rotational direction is has at a digit position
    analyze_loops("left carriage")
    [FPx,FPy] = [FP3x,FP3y]  #same for FP3
    FP_angles =  FP3_angle
    analyze_loops("right carriage")
    
else: #Babbage's Plan 27 from A/093, July 28, 1841
    names = ["L", "I1", "I"]
    DP = [8,8,8]
    threshold = 0.0 #degrees how far off a "good" mesh can be: only record the best
    FP_teeth = 48
    RP_tooth_range = range(22,23) #RP fixed at 22 teeth
    FC_tooth_range = range(30,31) #FC fixed at 30 teeth
    RP_angles = [58, 59, 1] #only do 58 degree as measured on A/093
    FP_angles = [0, 2*360/FP_teeth, .05] #do 2 digit cycles of the 48-tooth FP
    [FPx,FPy] = [0.0, 0.0]  #locate FP
    analyze_loops("Babbage", FCright=False)