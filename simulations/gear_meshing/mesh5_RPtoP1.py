'''
This is a program to analyze linked 5-gear train loops and tweak the axle locations
so that the gears mesh correctly all around all loops. It deals with meshes that
are made with concentric gears of different diametral pitches, like for the
Analytical Engine Plan 27 long pinions.

This also deals with the constraint imposed by pinions that mesh with the Plan 27 rack,
all of which must mesh simultaneously.

Since we don't know how to do this analytically, we combinatorily perturb the axle
locations consistent with the required axle-to-axle distances, and search the several
hundred thousand configurations for ones with an acceptable mesh discrepancy, of
less than 0.5 degrees. Of those, we pick the one whose largest coordinate change for
any of the axles (other than the rack pinion) is the smallest.

Usage notes:
    - Make a Solidworks assembly that has a sketch with all 22 gears in in their approximate right positions.
    - Add annotation notes close to the center of each gear with the axle names:
      A, P12, FP1, MP1, P11, RP1, P14, B, P13, P22, FP2, MP2, P21, RP2, P24, C, P23, P32, FP3, MP3, P31, RP3
    - Edit the sketch that shows the gear as circles at the contact diameter (#teeth/diametral pitch).
    - Run the Solidworks macro point_coords and export the labeled points to c:\temp\outpoints.txt.
      It will do so for any note that is within 0.5" of a point (presumably the center of a gear cirle), 
      and will use the note as the name of the point, as in "[P32x, P32y] = [6.55525386, -2.38900982]"
    - Import that file as assignments in the main program at the bottom of this file.
    - Run this program to solve for the best perturbations of the gear centers.
      If successful in finding a solution, it will write the new  and the original coordinates
      to c:\temp\inpoints.txt, as in "6.44277449, -2.46403619,    6.55525386, -2.38900982,  P32"
      The axle name from the note is just there as a comment.
    - Run the Solidworks macro point_coords with the original sketch open for editing, and 
      import the coordinates from c:\temp\inpoints.txt. It will find each of the circles based on
      the old coordinates of the center, and change the center to be at the new coordinates.
    - Save it as a new assembly so that you retain the original file with the original coordinates. That way
      you can run this program again starting with them, possibly with changes to the algorithm parameters.

Len Shustek, June 2025
7/8/2025:   - Add the middle and right groups to complete the Plan 27 Mill layout
7/10/2025:  - Add (and debug) the requirement to have the rack pinions RP
              (Babbage's O pinions) mesh with the rack
7/13/2025:  - Add additional constraints to avoid having RP interfere with P.1 or P.3
7/15/2024:  - Change rack pinion RP to mesh with P1 instead of MP, which reduces the gear train
              between the Mill and the Store from 6 to 5, including the rack. It also has the advantage 
              that the wheels iturn in opposite directions when linked for giving off, so the numbering 
              can be in the same direction for both Mill and Store.
            - Add additional contstraints to avoid RP with MP interference, now that RP links P1 
              to the rack
'''
# Angles are (mostly) measured here as counter-clockwise degrees from the horizontal X axis going to the right from the center of the circle

import math, copy, time, datetime
from mesh_routines_1 import *

def show_results(name, bestpos, startingpos, teeth, DP_in, DP_out, initial_angle=None):
    print(F"for the {name} loop with initial tooth angle of {initial_angle:.4f} from the horizontal")
    #print(bestpos)
    diffs = [(t1[0]-t2[0], t1[1]-t2[1]) for t1, t2 in zip(bestpos, startingpos)]
    print("  coordinate changes are", [f"{x[0]:.4f}, {x[1]:.4f}" for x in diffs])
    message, discrep, pitch_discrep, angles = verify_gear_tooth_alignment_angular(name, 5, bestpos, teeth, DP_in, DP_out, initial_angle=initial_angle, verbose=False)
    print(message)
    return angles

def analyze_loops(group, starting_angle=0.0, bothloops=True, rackgear=False, checkRPtoP1=False, checkRPtoP3=False, checkRPtoMP=False):
    ''' 
    This analyzes the two loops of gears in he left, middle, or right groups of the Plan 27 Mill 
    input for the left loop:  teeth1, startingpos1, DP_in1, DP_out1
    input for the right loop: teeth2, startingpos2, DP_in2, DP_out2
    output: bestpos1, bestpos2, angle_RW, angle_P1, angle_RP, angle_FP, RP discrepancies
    ''' 
    print(f"\n******* analyzing the {group} group *******\n")
    print(f"for the starting coordinates of left loop with starting angle of {starting_angle} degrees for the left wheel")
    message, discrep, pitch_discrep, angles1 = verify_gear_tooth_alignment_angular("left", 5, startingpos1, teeth1, DP_in1, DP_out1, initial_angle=starting_angle)
    print(message)
    if bothloops:
        print(f"and for the starting coordinates of the right loop")
        message, discrep, pitch_discrep, angles2 = verify_gear_tooth_alignment_angular("right", 5, startingpos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[2])
        print(message)
    
    [[LWx,LWy],[P2x,P2y],[FPx,FPy],[MPx,MPy],[P1x,P1y],[RPx,RPy]] = startingpos1
    RPxbest = RPx
    LWtoP2 = math.dist([LWx,LWy],[P2x,P2y])
    P2toFP = math.dist([P2x,P2y],[FPx,FPy])
    FPtoMP = math.dist([FPx,FPy],[MPx,MPy])
    MPtoP1 = math.dist([MPx,MPy],[P1x,P1y])
    P1toLW = math.dist([P1x,P1y],[LWx,LWy])
    P1toRP = math.dist([RPx,RPy],[P1x,P1y]) #required distance from P1 to RP -- but RPy must not change because it connects to the rack!
   
    if bothloops:
       [[FPx,FPy],[P4x,P4y],[RWx,RWy],[P3x,P3y],[MPx,MPy]] = startingpos2
       RWtoP3 = math.dist([P3x,P3y],[RWx,RWy])
       P3toMP = math.dist([P3x,P3y],[MPx,MPy])
       FPtoP4 = math.dist([FPx,FPy],[P4x,P4y])
       P4toRW = math.dist([P4x,P4y],[RWx,RWy])
    if checkRPtoP3:
        RPtoP3separation = non_interference_distance(teeth1[llRPndx], DP_in1[llRPndx], teeth2[rlP3ndx], DP_in2[rlP3ndx])
    if checkRPtoP1:
        RPtoP1separation = non_interference_distance(teeth1[llRPndx], DP_in1[llRPndx], teeth1[llP1ndx], DP_in1[llP1ndx])
    if checkRPtoMP:
        RPtoMPseparation = non_interference_distance(teeth1[llRPndx], DP_in1[llRPndx], teeth1[llMPndx], DP_in1[llMPndx])
        
    best = 99
    bestRP = 99
    worstRP = 0
    chosenRP = 00
    RP_discrep = 0
    delta = .20
    steps = 50
    maxdegerr = 0.5 #maximum allowed meshing error in degrees for other than RP
    maxRPdegerr = 0.5  #maximum allowed meshing error in degrees for RP
    incr = delta/steps
    [nleftgood, nrightgood] = [0,0]
    debug=0
    ''' OUR SEARCH PLAN FOR NEW AXLE POSITIONS FOR ONE PLAN 27 GROUP
    gear loop 1 is LW to P2 to FP to MP to P1
    gear loop 2 is FP to P4 to RW to P3 to MP
    rack gear is MP to RP, then to linear rack
    while tweaking P2y:
        compute P2x by distance to LW
        compute [FPx, FPy] by distance to P2 and MP
        while tweaking FPx:
            compute FPy by distance to P2
            compute [MPx, MPy] by distance to FP and P1
            while tweaking MPx:
                compute MPy by distance to FP
                while tweaking MPy:
                    compute MPx by distance to FP
                    compute [P1x, P1y] by distance to MP and LW
                    compute RPx by distance to P1 (RPy never changes!)
                    analyze loop 1 for final gear discrepancy
                    if rackgear, include RP meshing discrepancy
                    if the discrepancies are acceptable:
                        if bothloops:
                        while tweaking P4y:
                            compute P4x by distance to FP
                            compute [RWx, RWy] by distance to P4 and P3
                            while tweaking P3y:
                                compute P3x by distance to MP
                                compute [RWx, RWy] by distance to P4 and P3 
                                analyze loop 2 for final gear discrepancy
                                if the discrepancies are acceptable:
                                    if the maximum coordinate displacement for both loops is the minimum so far
                                        remember the coordinates for both loops
                        else #only left loop
                        if the maximum coordinate displacement for the left loop is the minimum so far
                            remember the coordinates of the left loop
    '''
    print(f'\ndoing coordinate search for meshing {"both loops" if bothloops else "left loop"} of the {group} group...')
    
    P2yp = P2y - incr*steps/2
    for P2step in range(steps):
        P2yp += incr
        P2xp = fix_coord(P2x, P2yp, LWx, LWy, LWtoP2)
        if P2xp is None: continue
        newpos = set_by_distance([P2xp,P2yp],P2toFP, [MPx,MPy],FPtoMP, [FPx,FPy])
        if not newpos: continue
        [FPxp, FPyp] = newpos
        
        FPxp = FPxp - incr*steps/2
        for FPstep in range(steps):
            FPxp += incr
            FPyp = fix_coord(FPyp, FPxp, P2yp, P2xp, P2toFP)  
            if FPyp is None: continue
            newpos = set_by_distance([FPxp,FPyp],FPtoMP, [P1x,P1y],MPtoP1, [MPx,MPy])
            if not newpos: continue
            [MPxp, MPyp] = newpos
            
            MPxp = MPxp - incr*steps/2
            for MPstepx in range(steps):
                
                MPyp = MPyp - incr*steps/2
                for MPstep2 in range(steps):
                    MPyp += incr
                    MPxpp = fix_coord(MPxp, MPyp, FPxp, FPyp, FPtoMP)
                    if MPxpp is None: continue
                    MPtoFP = math.dist([MPxpp,MPyp],{FPxp,FPyp})
                    newpos = set_by_distance([MPxpp,MPyp],MPtoP1, [LWx,LWy],P1toLW, [P1x,P1y])
                    if not newpos: continue
                    [P1xp, P1yp] = newpos
                    if doRP:
                        RPxp = fix_coord(RPx, RPy, P1xp, P1yp, P1toRP) #can only change RPx, not RPy, because it meshes with the rack
                        if RPxp is None: continue
                    else: RPxp = RPx
                    axlepos1 = [[LWx,LWy], [P2xp,P2yp], [FPxp,FPyp], [MPxpp,MPyp], [P1xp,P1yp]]
                    #print(f"new dist MP to FP was: {newMPtoFP}")
                    message1, discrep1, pitch_discrep1, angles1 = verify_gear_tooth_alignment_angular("left", 5, axlepos1, teeth1, DP_in1, DP_out1, initial_angle=starting_angle)
                    if rackgear: #see how out of mesh the rack pinion (RP2 or RP3) is with the rack
                        RP_degrees_per_tooth = 360 / teeth1[llRPndx]
                        RPtoRP1 = RPxp - RP1xn #distance between RP1 and this RP (RP2 or RP3)
                        RPradius = (teeth1[llRPndx] / DP_out1[llRPndx])/2 #radius of an RP
                        delta_angle = (RPtoRP1 / RPradius) # needed angular difference from RP1 to this RP in radians
                        delta_angle = delta_angle * 180.0 / math.pi #needed angular difference in degrees
                        delta_angle = delta_angle % RP_degrees_per_tooth #as part of a tooth angle
                        #See what angle RP1 (the first RP) is at, based on the angle of P11 that it meshes to
                        RP1_angle = calculate_meshing_tooth_angle(teeth1[llP1ndx], leftbestpos1[llP1ndx], teeth1[llRPndx], leftbestpos1[llRPndx], P11_angle)
                        RP_required_angle = RP1_angle + delta_angle #the angle we need this new RP to be
                        RP_required_angle = RP_required_angle % RP_degrees_per_tooth #as part of a tooth angle
                        #See what angle this RP (RP2 or RP3) is at, based on the angle of its P1 (P21 or P31) that we just calculated
                        RP_angle = calculate_meshing_tooth_angle(teeth1[llP1ndx], [P1xp,P1yp], teeth1[llRPndx], [RPxp,RPy], angles1[llP1ndx])
                        #no! RP_angle += 180.0/teeth1[llRPndx] #offset by a half tooth because a tooth fits a valley?
                        RP_angle = RP_angle % RP_degrees_per_tooth # as part of a tooth angle
                        RP_discrep = abs(RP_angle - RP_required_angle)
                        if RP_discrep > worstRP: worstRP = RP_discrep
                        if RP_discrep < bestRP: bestRP = RP_discrep
                    if checkRPtoP1:
                        RPtoP1distance  = math.dist([RPxp,RPy],[P1xp,P1yp])
                    if checkRPtoMP:
                        RPtoMPdistance = math.dist([RPxp,RPy],[MPxpp,MPyp] )
                    if (abs(discrep1) < maxdegerr and 
                       (not rackgear or RP_discrep < maxRPdegerr) and 
                       (not checkRPtoP1 or RPtoP1distance > RPtoP1separation) and 
                       (not checkRPtoMP or RPtoMPdistance > RPtoMPseparation)): 
                        nleftgood += 1 #left loop is good!
                        if bothloops:
                            
                            P4yp = P4y - incr*steps/2
                            for P4step in range(steps):
                                P4yp += incr
                                P4xp = fix_coord(P4x, P4yp, FPxp, FPyp, FPtoP4)
                                if P4xp is None: continue
                                newpos = set_by_distance([P4xp,P4yp], P4toRW, [P3x,P3y], RWtoP3, [RWx,RWy])
                                if not newpos: continue
                                if newpos[1] < RWy: continue #if wheel drops, next group is hard/impossible to solve
                                [RWxp, RWyp] = newpos
                                
                                P3yp = P3y - incr*steps/2
                                for P3step in range(steps):
                                    P3yp += incr
                                    P3xp = fix_coord(P3x, P3yp, MPxpp, MPyp, P3toMP)
                                    if P3xp is None: continue
                                    newpos = set_by_distance([P4xp,P4yp], P4toRW, [P3xp,P3yp], RWtoP3, [RWxp,RWyp])
                                    if not newpos: continue
                                    if newpos[1] < RWy: continue #if wheel drops, next group is hard/impossible to solve
                                    [RWxp, RWyp] = newpos
                                    axlepos2 = [[FPxp,FPyp],[P4xp,P4yp],[RWxp,RWyp],[P3xp,P3yp],[MPxpp,MPyp]]
                                    message2, discrep2, pitch_discrep2, angles2 = verify_gear_tooth_alignment_angular("right", 5, axlepos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[2])
                                    #check for additional constraints here
                                    if checkRPtoP3:
                                        RPtoP3distance = math.dist([RPxp,RPy],[P3xp,P3yp])
                                    if abs(discrep2) < maxdegerr and (not checkRPtoP3 or RPtoP3distance > RPtoP3separation): #both loops ok
                                        nrightgood += 1
                                        maxdiff1 = max(max(abs(v1[0]-v2[0]), abs(v1[1]-v2[1])) for v1,v2 in zip(axlepos1, startingpos1))
                                        maxdiff2 = max(max(abs(v1[0]-v2[0]), abs(v1[1]-v2[1])) for v1,v2 in zip(axlepos2, startingpos2))
                                        maxdiff = max(maxdiff1, maxdiff2)
                                        if maxdiff < best: # keep the smallest maximum displacement of axle centers from the initial position
                                            best = maxdiff
                                            bestpos1 = copy.deepcopy(axlepos1)
                                            bestpos1.append([RPxp,RPy]) #return the rack pinion coordinates as the last one of the left gear loop
                                            bestpos2 = copy.deepcopy(axlepos2)
                                            chosenRP = RP_discrep
                        else: #only left loop
                            maxdiff = max(max(abs(v1[0]-v2[0]), abs(v1[1]-v2[1])) for v1,v2 in zip(axlepos1, startingpos1))
                            if maxdiff < best:
                                best = maxdiff
                                bestpos1 = copy.deepcopy(axlepos1)
                                bestpos1.append([RPxp,RPy]) #return the rack pinion coordinates as the last one of the left gear loop
                                bestpos2 = []
                                chosenRP = RP_discrep
    if bothloops:
        print(f"after {steps**6:,} possible combinations with {nleftgood:,} left good and {nrightgood:,} right good solutions")
    else:                    
        print(f"after {steps**3:,} possible combinations with {nleftgood:,} left good solutions")
    if best == 99:
        print("----- no solution!")
        exit(0)
    print(f"the best axle locations have a {best:.4f} inch maximum coordinate change (not including the rack pinion)")
    angles1 = show_results("left", bestpos1, startingpos1, teeth1, DP_in1, DP_out1, initial_angle=starting_angle)
    print(f"the angle of the FP is {angles1[llFPndx]:.6f} degrees counter-clockwise from horizontal to the right")
    
    if bothloops:
        angles2 = show_results("right", bestpos2, startingpos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[llFPndx])
        return bestpos1, bestpos2, angles2[rlRWndx], angles1[llP1ndx], angles1[llFPndx], [chosenRP, bestRP, worstRP]
    else:
        return bestpos1, bestpos2, None, angles1[llP1ndx], angles1[llFPndx], [chosenRP, bestRP, worstRP]
    #end of analyze_loops
   
def non_interference_distance(teeth1, DP1, teeth2, DP2):
#compute the required separation between two gears so they don't interfere
    adden1 = (teeth1+2)/DP1  #addendum circle diameter
    adden2 = (teeth2+2)/DP2
    return (adden1+adden2)/2 + 0.1 #return separation plus 0.1" of slop

start_cpu_time = time.process_time()
print(f"\r\nPlan 27 loop analysis started {datetime.datetime.now()}")

if False: #Babbage's Plan 27 gears from drawing A/093
    names1 = ["''A", "''J", "''L", "''S", "''G"]  #left gear loop
    teeth1 = [80, 30, 48, 40, 28] 
    startingpos1 = [[5.21155228486686,7.35374093869765], [9.92857461043897,4.52536678027126], [13.6682120824508,3.41851919459165], [13.6973448504943,8.91844203785283], [10.3050459445236,9.14715175026213]]
    DP_in1 = [10, 10, 10, 8, 10]
    DP_out1= [10, 10, 8, 10, 10]
    A_angle = 0.0

    names2 = ["''L", " 'J", " 'A", " 'G", "''S"]  #right gear loop, which shares ''L and ''S with the first loop
    teeth2 = [ 48, 30, 80, 28, 40] 
    startingpos2 = [[13.6682120824508,3.41851919459165], [17.4051954188825,4.53429495308097], [22.1872002770905,7.25135762002012], [17.094872612042,9.04807656069539], [13.6973448504943,8.91844203785283]]
    DP_in2 = [8, 10, 10, 10, 10]
    DP_out2= [10, 10, 10, 10, 8]
    
    analyze_loops("left")
    
if True: #my prototype version 5 gears
    #to avoid letter modifiers we have renamed ''J to P12, ''L to FP1, ''S to MP1, ''G to P11, 'J to P12, 'G to P13, 'S to B, and O to RP
    namesLL = ["  A", "P12", "FP1", "MP1", "P11", "RP1"]  #left gear loop plus rack pinion
    namesLM = ["  B", "P22", "FP2", "MP2", "P21", "RP2"] 
    namesLR = ["  C", "P32", "FP3", "MP3", "P31", "RP3"] 
    llFPndx = 2 #the 3rd in the list for the left loop is FP
    llMPndx = 3 #the 4th in the list for the left loop is MP
    llP1ndx = 4 #the 5th in the list for the left loop is P.1
    llRPndx = 5 #the 6th in the list for the left loop is RP
    teeth1 = [20, 20, 16, 16, 20, 20] #counterclockwise: LW, P.2, FP., MP., P.1
    DP_in1 = [8, 8, 8, 5, 8, 8]
    DP_out1= [8, 8, 5, 8, 8, 8]
    A_angle = 0.0

    namesRL = ["FP1", "P14", "  B", "P13", "MP1"]  #right gear loop, which shares MP1 and FP1 with the first loop
    namesRM = ["FP2", "P24", "  C", "P23", "MP2"]
    rlRWndx = 2 #where the right wheel is in the right gear loop list
    rlP3ndx = 3 #where the P.3 pinion is in the right gear loop list
    teeth2 = [16, 20, 20, 20, 16] #counterclockwise: FP., P.4, RW, P.3, MP.
    DP_in2 = [5, 8, 8, 8, 8]
    DP_out2= [8, 8, 8, 8, 5]
    
    #the assignments below are automatically generated by the Solidworks point_coords macro
    #from the sketch that shows the initial desied positions of all 22 gears
    if True: #from sketch 4 of gear mesh study 1 P1 norels
        [P32x, P32y] = [6.69856114766717, -2.50749417454102]
        [FP3x, FP3y] = [8.92847993577694, -2.80743116531585]
        [MP3x, MP3y] = [8.94856114766717, 0.392505825458977]
        [RP3x, RP3y] = [5.7187652505539, 2.69250582545898]
        [P31x, P31y] = [6.69856114766717, 0.392505825458977]
        [Cx, Cy] = [4.66201996222554, -1.05749417454102]
        [P23x, P23y] = [2.62916961268324, 0.397675731815533]
        [P24x, P24y] = [2.62180771824152, -2.50232426818447]
        [MP2x, MP2y] = [0.382364977016221, 0.517546200010218]
        [FP2x, FP2y] = [0.379029535270685, -2.68245206168124]
        [P22x, P22y] = [-1.86415787057115, -2.50749417454102]
        [P21x, P21y] = [-1.86415787057115, 0.392505825458977]
        [Bx, By] = [-3.90069905601279, -1.05749417454102]
        [RP2x, RP2y] = [-2.84395376768443, 2.69250582545898]
        [P13x, P13y] = [-5.93724024145442, 0.392505825458977]
        [P14x, P14y] = [-5.93724024145442, -2.50749417454102]
        [P12x, P12y] = [-10.4272291055832, -2.50749417454102]
        [MP1x, MP1y] = [-8.18223467351879, 0.542505825458953]
        [P11x, P11y] = [-10.4272291055832, 0.392505825458977]
        [RP1x, RP1y] = [-11.4070250026964, 2.69250582545898]
        [Ax, Ay] = [-12.4637702910248, -1.05749417454102]
        [FP1x, FP1y] = [-8.18223467351879, -2.65749417454105]

    doRP = True

# configure left group
    startingpos1 = [[Ax,Ay],[P12x,P12y],[FP1x,FP1y],[MP1x,MP1y],[P11x,P11y],[RP1x,RP1y]]
    startingpos2 = [[FP1x,FP1y],[P14x,P14y],[Bx,By],[P13x,P13y],[MP1x,MP1y]]
    leftbestpos1, leftbestpos2, B_angle, P11_angle, FP1_angle, RPdiscreps = analyze_loops("left", checkRPtoMP=doRP)  
    [RP1xn,RP1yn] = leftbestpos1[llRPndx] #note the new position of the first rack pinion
    while P11_angle < 0:  
        P11_angle += 360 #make it positive
    
#configure middle group
    Bnew = leftbestpos2[rlRWndx] #the new jiggled starting position of B
    print(f"wheel B moved by delta x {Bnew[0]-Bx:.4f}, delta y {Bnew[1]-By:.4f}")
    #since B jiggled, jiggle P21 and P22 to be consistent
    BtoP22 = math.dist([Bx,By],[P22x,P22y]) #required distances
    BtoP21 = math.dist([Bx,By],[P21x,P21y])
    P22toFP2 = math.dist([P22x,P22y],[FP2x,FP2y])
    P21toMP2 = math.dist([P21x,P21y],[MP2x,MP2y])
    P21toRP2 = math.dist([P21x,P21y],[RP2x,RP2y])
    [P22xn,P22yn] = checkdist("P22", set_by_distance(Bnew, BtoP22, [FP2x,FP2y], P22toFP2, [P22x,P22y]))
    [P21xn,P21yn] = checkdist("P21", set_by_distance(Bnew, BtoP21, [MP2x,MP2y], P21toMP2, [P21x,P21y]))
    RP2xn = fix_coord(RP2x, RP2y, P21xn, P21yn, P21toRP2) #change RPx (not RPy) to maintain distance to P1
    startingpos1 = [Bnew,[P22xn,P22yn],[FP2x,FP2y],[MP2x,MP2y],[P21xn,P21yn],[RP2xn,RP2y]]
    startingpos2 = [[FP2x,FP2y],[P24x,P24y],[Cx,Cy],[P23x,P23y],[MP2x,MP2y]]
    midbestpos1, midbestpos2, C_angle, P21_angle, FP2_angle, RPdiscreps = analyze_loops("middle", starting_angle=B_angle, rackgear=doRP, checkRPtoMP=doRP) 
    print(f"the rack pinion angular discrepancy is {RPdiscreps[0]:.3f} degrees. (best was {RPdiscreps[1]:.3f}, worst was {RPdiscreps[2]:.3f})")
    
#configure right group
    Cnew = midbestpos2[rlRWndx]  #the new jiggled starting position of C
    print(f"wheel C moved by delta x {Cnew[0]-Cx:.4f}, delta y {Cnew[1]-Cy:.4f}")
    #in order to be able to tweak the right group into consistency, we shift all its gears left or right by the amount that C moved left or right
    Cdeltax = Cnew[0]-Cx 
    P31xn = P31x + Cdeltax
    P32xn = P32x + Cdeltax
    FP3xn = FP3x + Cdeltax
    MP3xn = MP3x + Cdeltax
    RP3xn = RP3x + Cdeltax
    doright = True
    if doright:
        #now try to jiggle P31 and P32 to be consistent
        CtoP32 = math.dist([Cx,Cy],[P32x,P32y]) #required distances
        CtoP31 = math.dist([Cx,Cy],[P31x,P31y])
        P32toFP3 = math.dist([P32x,P32y],[FP3x,FP3y])
        P31toMP3 = math.dist([P31x,P31y],[MP3x,MP3y])
        P31toRP3 = math.dist([P31x,P31y],[RP3x,RP3y])
        [P32xn,P32yn] = checkdist("P32", set_by_distance(Cnew, CtoP32, [FP3xn,FP3y], P32toFP3, [P32xn,P32y]))
        [P31xn,P31yn] = checkdist("P31", set_by_distance(Cnew, CtoP31, [MP3xn,MP3y], P31toMP3, [P31xn,P31y]))
        RP3xn = fix_coord(RP3xn, RP3y, P31xn, P31yn, P31toRP3) #change RPx (not RPy) to maintain distance to P1
        startingpos1 = [Cnew,[P32xn,P32yn],[FP3xn,FP3y],[MP3xn,MP3y],[P31xn,P31yn],[RP3xn,RP3y]]
        startingpos2 = None
        RP2toRP3 = math.dist(midbestpos1[5],[RP3xn,RP3y]) #distance from the new position of RP2 to RP3
        rightbestpos1, rightbestpos2, D_angle, P31_angle, FP3_angle, RPdiscreps = analyze_loops("right", bothloops=False, starting_angle=C_angle, rackgear=doRP, checkRPtoMP=doRP) 
        print(f"the rack pinion angular discrepancy is {RPdiscreps[0]:.3f} degrees. (best was {RPdiscreps[1]:.3f}, worst was {RPdiscreps[2]:.3f})")

    filename = "c:\\temp\\inpoints.txt"
    print("\nfinal old and new coordinates:")
    def printpoint(textfile, old:tuple, new:tuple, name:str):
        string = f"{old[0]:12.8f},{old[1]:12.8f},  {new[0]:12.8f},{new[1]:12.8f},  {name}"
        print(string)
        textfile.write(f"{string}\n")
        return
    with open(filename, 'w') as textfile:
        printpoint(textfile, [Ax,Ay],     leftbestpos1[0],   namesLL[0])  #left group
        printpoint(textfile, [P12x,P12y], leftbestpos1[1],   namesLL[1])
        printpoint(textfile, [FP1x,FP1y], leftbestpos1[2],   namesLL[2])
        printpoint(textfile, [MP1x,MP1y], leftbestpos1[3],   namesLL[3])
        printpoint(textfile, [P11x,P11y], leftbestpos1[4],   namesLL[4])
        printpoint(textfile, [RP1x,RP1y],   leftbestpos1[5],   namesLL[5])
        printpoint(textfile, [P14x,P14y], leftbestpos2[1],   namesRL[1])
        printpoint(textfile, [Bx,By],     leftbestpos2[2],   namesRL[2])
        printpoint(textfile, [P13x,P13y], leftbestpos2[3],   namesRL[3])
        printpoint(textfile, [P22x,P22y], midbestpos1[1],    namesLM[1])  #middle group
        printpoint(textfile, [FP2x,FP2y], midbestpos1[2],    namesLM[2])
        printpoint(textfile, [MP2x,MP2y], midbestpos1[3],    namesLM[3])
        printpoint(textfile, [P21x,P21y], midbestpos1[4],    namesLM[4])
        printpoint(textfile, [RP2x,RP2y], midbestpos1[5],    namesLM[5])
        printpoint(textfile, [P24x,P24y], midbestpos2[1],    namesRM[1])
        printpoint(textfile, [Cx,Cy],     midbestpos2[2],    namesRM[2])
        printpoint(textfile, [P23x,P23y], midbestpos2[3],    namesRM[3])
        if doright:
            printpoint(textfile, [P32x,P32y], rightbestpos1[1],  namesLR[1])  #right group
            printpoint(textfile, [FP3x,FP3y], rightbestpos1[2],  namesLR[2])
            printpoint(textfile, [MP3x,MP3y], rightbestpos1[3],  namesLR[3])
            printpoint(textfile, [P31x,P31y], rightbestpos1[4],  namesLR[4])
            printpoint(textfile, [RP3x,RP3y], rightbestpos1[5],  namesLR[5])
        else:
            printpoint(textfile, [P32x,P32y], [P32xn,P32y],  namesLR[1])  #right group (only shifted)
            printpoint(textfile, [FP3x,FP3y], [FP3xn,FP2y],  namesLR[2])
            printpoint(textfile, [MP3x,MP3y], [MP3xn,MP3y],  namesLR[3])
            printpoint(textfile, [P31x,P31y], [P31xn,P31y],  namesLR[4])
        print(f"wrote these new coordinates to {filename}")

    filename = "c:\\temp\FPconfig.txt"
    print("\nFP configuration for the 3-gear analysis:")
    def printFPconfig(textfile, num, coords, angle):
        string = f"    [FP{num}x,FP{num}y] = [{coords[0]:7},{coords[1]:7}]\n    FP{num}_angle = {angle:.7}"
        print(string)
        textfile.write(f"{string}\n")
    with open(filename, 'w') as textfile:
        printFPconfig(textfile, 2, midbestpos1[llFPndx], FP2_angle)
        if doright: printFPconfig(textfile, 3, rightbestpos1[llFPndx], FP3_angle)
    print(f"wrote these to {filename}")
    #endif my prototype
        
print(f"the analysis took {time.process_time()-start_cpu_time:.0f} seconds")   
