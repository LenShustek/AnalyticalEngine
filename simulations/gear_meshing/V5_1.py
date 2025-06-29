'''
This is a program to analyze two linked gear train loops and tweak the axle locations
so that the gears mesh correctly all around both circles. It deals with meshes that
are made with concentric gears of different diametral pitches, as happens for the
Analytical Engine Plan 27 long pinions.

Since we don't know how to do this analytically, we combinatorily perturb the axle
locations consistent with the required axle-to-axle distances, and search the several
hundred thousand of configurations for ones with an acceptable mesh discrepancy of
less than .01 degrees. Of those, we pick the one whose largest coordinate change for
any of the axles is the smallest among all the acceptable configurations.

Len Shustek, June 2025
'''

import math, copy
from mesh_routines_1 import *

def show_results(name, bestpos, startingpos, teeth, DP_in, DP_out, initial_angle=None):
    print(F"**** results for {name} loop with intial angle {initial_angle}")
    print(bestpos)
    diffs = [(t1[0]-t2[0], t1[1]-t2[1]) for t1, t2 in zip(bestpos, startingpos)]
    print("coordinate changes:", [f"{x[0]:.4f}, {x[1]:.4f}" for x in diffs])
    answer, message, discrep, pitch_discrep, angles = verify_gear_tooth_alignment_angular(bestpos, teeth, DP_in, DP_out, initial_angle=initial_angle, verbose=False)
    print(message)
    return angles

Plan27 = False

if Plan27: #Babbage's Plan 27 gears from drawing A/093
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
    
else: #my prototype version 5 gears
    #to avoid letter modifiers we have renamed ''J to P12, ''L to FP1, ''S to MP1, ''G to P11, 'J to P12, 'G to P13, and 'S to B
    names1 = ["  A", "P12", "FP1", "MP1", "P11"]  #left gear loop
    teeth1 = [20, 20, 16, 16, 20] #counterclockwise: A, P12, FP1, MP1, P11
    startingpos1 = [[-12.5673957459426,-1.1977050217781], [-10.5308545605009,-2.64770502177811], [-8.28586012843658,-2.7977050217781], [-8.28586012843658,0.402294978221896], [-10.5308545605009,0.252294978221894]]
    DP_in1 = [8, 8, 8, 5, 8]
    DP_out1= [8, 8, 5, 8, 8]
    A_angle = 0.0

    names2 = ["FP1", "P14", "  B", "P13", "MP1"]  #right gear loop, which shares MP1 and FP1 with the first loop
    teeth2 = [ 16, 20, 20, 20, 16] #counterclockwise: FP1, P14, B, P13, MP1
    startingpos2 = [[-8.28586012843658,-2.7977050217781], [-6.04086569637222,-2.64770502177811], [-4.00432451093059,-1.19770502177811], [-6.04086569637222,0.252294978221894], [-8.28586012843658,0.402294978221896]]
    DP_in2 = [5, 8, 8, 8, 8]
    DP_out2= [8, 8, 8, 8, 5]

print(f"\nfor these starting coordinates of left loop with starting angle of {A_angle} degrees\n{startingpos1}")
answer, message, discrep, pitch_discrep, angles1 = verify_gear_tooth_alignment_angular(startingpos1, teeth1, DP_in1, DP_out1, initial_angle=A_angle)
print(message)
print(f"and for these starting coordinates of the right loop\n{startingpos2}")
answer, message, discrep, pitch_discrep, angles2 = verify_gear_tooth_alignment_angular(startingpos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[2])
print(message)

angle = 0.0
best = 999.0
tries=0
while angle < 360.0/teeth1[0]:  #find the best possible angle position for a mesh of the left loop
    answer, message, discrep, pitch_discrep, angles1 = verify_gear_tooth_alignment_angular(startingpos1, teeth1, DP_in1, DP_out1, initial_angle=angle)
    if abs(discrep) < best:
        best = abs(discrep)
        bestangle = angle
    angle += .01
    tries += 1
print(f"\nafter {tries} tries, the best starting angle is {bestangle:4f}")
answer, message, discrep, pitch_discrep, angles1 = verify_gear_tooth_alignment_angular(startingpos1, teeth1, DP_in1, DP_out1, initial_angle=bestangle)
print(message)
print("which for the right loop means:")
answer, message, discrep, pitch_discrep, angles2 = verify_gear_tooth_alignment_angular(startingpos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[2])
print(message)
A_angle = bestangle #use the discovered angle as the starting angle from now on

[[Ax,Ay],[P12x,P12y],[FP1x,FP1y],[MP1x,MP1y],[P11x,P11y]] = startingpos1
[[FP1x,FP1y],[P14x,P14y],[Bx,By],[P13x,P13y],[MP1x,MP1y]] = startingpos2

AtoP12 = math.dist([Ax,Ay],[P12x,P12y])
P12toFP1 = math.dist([P12x,P12y],[FP1x,FP1y])
FP1toMP1 = math.dist([FP1x,FP1y],[MP1x,MP1y])
MP1toP11 = math.dist([MP1x,MP1y],[P11x,P11y])
P11toA = math.dist([P11x,P11y],[Ax,Ay])
BtoP13 = math.dist([P13x,P13y],[Bx,By])
P13toMP1 = math.dist([P13x,P13y],[MP1x,MP1y])
FP1toP14 = math.dist([FP1x,FP1y],[P14x,P14y])
P14toB = math.dist([P14x,P14y],[Bx,By])

best = 99
delta = .1
steps = 50
maxdegerr = .01 #maximum allowed meshing error in degrees
incr = delta/steps
ntries = 0
ngood = 0
debug=0
''' OUR SEARCH PLAN FOR NEW AXLE POSITIONS
gear loop 1 is A to P12 to FP1 to MP1 to P11
gear loop 2 is FP1 to P14 to B to P13 to MP1
while tweaking P12y:
    compute P12x by distance to A
    compute [FP1x, FP1y] by distance to P12 and MP1
    while tweaking FP1x:
        compute FP1y by distance to P12
        compute [MP1x, MP1y] by distance to FP1 and P11
        while tweaking MP1x:
            compute MP1y by distance to FP1
            compute [P11x, P11y] by distance to MP1 and A
            analyze loop 1, and if the discrepancy is less than .01 degrees:
                while tweaking P14y:
                    compute P14x by distance to FP1
                    compute [Bx, By] by distance to P14 and P13
                    while tweaking P13y:
                        compute P13x by distance to MP1
                        compute [Bx, By] by distance to P14 and P13 
                        analyze loop 2, and if the discrepancy is less than .01 degrees:
                            remember these coordinates if the maximum coordinate displacement is the minimum so far
'''
print("\nstarting coordinate search...")
P12yp = P12y - incr*steps/2
for P12step in range(steps):
    P12yp += incr
    P12xp = fix_coord(P12x, P12yp, Ax, Ay, AtoP12)
    if P12xp is None: continue
    newpos = set_by_distance([P12xp,P12yp],P12toFP1, [MP1x,MP1y],FP1toMP1, [FP1x,FP1y])
    if not newpos: continue
    [FP1xp, FP1yp] = newpos
    FP1xp = FP1xp - incr*steps/2
    for FP1step in range(steps):
        FP1xp += incr
        FP1yp = fix_coord(FP1y, FP1xp, P12yp, P12xp, P12toFP1)  
        if FP1yp is None: continue
        newpos = set_by_distance([FP1xp,FP1yp],FP1toMP1, [P11x,P11y],MP1toP11, [MP1x,MP1y])
        if not newpos: continue
        [MP1xp, MP1yp] = newpos
        MP1xp = MP1xp - incr*steps/2
        for MP1step in range(steps):
            MP1xp += incr
            MP1yp = fix_coord(MP1y, MP1xp, FP1yp, FP1xp, FP1toMP1)
            if MP1yp is None: continue
            newpos = set_by_distance([MP1xp,MP1yp],MP1toP11, [Ax,Ay],P11toA, [P11x,P11y])
            if not newpos: continue
            [P11xp, P11yp] = newpos
            axlepos1 = [[Ax,Ay], [P12xp,P12yp], [FP1xp,FP1yp], [MP1xp,MP1yp], [P11xp,P11yp]]
            answer1, message1, discrep1, pitch_discrep1, angles1 = verify_gear_tooth_alignment_angular(axlepos1, teeth1, DP_in1, DP_out1, initial_angle=A_angle)
            if not answer1:
                print(message1)
                print(P12step, FP1step, MP1step)
                exit(0)
            if abs(discrep1) < maxdegerr: #left loop is good; try to fix right loop
                P14yp = P14y - incr*steps/2
                for P14step in range(steps):
                    P14yp += incr
                    P14xp = fix_coord(P14x, P14yp, FP1xp, FP1yp, FP1toP14)
                    if P14xp is None: continue
                    newpos = set_by_distance([P14xp,P14yp], P14toB, [P13x,P13y], BtoP13, [Bx,By])
                    if not newpos: continue
                    [Bxp, Byp] = newpos
                    P13yp = P13y - incr*steps/2
                    for P13step in range(steps):
                        P13yp += incr
                        P13xp = fix_coord(P13x, P13yp, MP1xp, MP1yp, P13toMP1)
                        if P13xp is None: continue
                        newpos = set_by_distance([P14xp,P14yp], P14toB, [P13xp,P13yp], BtoP13, [Bxp,Byp])
                        if not newpos: continue
                        [Bxp, Byp] = newpos
                        axlepos2 = [[FP1xp,FP1yp],[P14xp,P14yp],[Bxp,Byp],[P13xp,P13yp],[MP1xp,MP1yp]]
                        answer2, message2, discrep2, pitch_discrep2, angles2 = verify_gear_tooth_alignment_angular(axlepos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[2])
                        if not answer2:
                            print(message2)
                            print(P12step, FP1step, MP1step, P14step, P13step)
                            exit(0)
                        ntries += 1
                        if abs(discrep2) < maxdegerr:  #error in degrees is very small
                            ngood += 1
                            maxdiff1 = max(abs(v1-v2) for t1,t2 in zip(axlepos1, startingpos1) for v1,v2 in zip(t1,t2))
                            maxdiff2 = max(abs(v1-v2) for t1,t2 in zip(axlepos2, startingpos2) for v1,v2 in zip(t1,t2))
                            maxdiff = max(maxdiff1, maxdiff2)
                            if maxdiff < best: # keep the smallest maximum displacement of axle centers from the initial position
                                best = maxdiff
                                bestpos1 = copy.deepcopy(axlepos1)
                                bestpos2 = copy.deepcopy(axlepos2)
                        debug += 1
                        if (debug > 1000000): #reduce for more frequent debugging output
                            print(P12step, FP1step, MP1step, P14step, P13step)
                            print(f"best: {best}, disrepancies: {discrep1}, {discrep2}")
                            print(axlepos1)
                            print(axlepos2)
                            debug = 0
print(f"\nafter {ntries} tries which found {ngood} solutions, the best axle locations with a {best:.4f} inch max coordinate change are")
angles1 = show_results("left", bestpos1, startingpos1, teeth1, DP_in1, DP_out1, initial_angle=A_angle)
angles2 = show_results("right", bestpos2, startingpos2, teeth2, DP_in2, DP_out2, initial_angle=angles1[2])

print("\nleft loop coordinates")
for i in range(5):
    print(f"{names1[i]}: {bestpos1[i][0]:11.6f},  {bestpos1[i][1]:11.6f}")
print("right loop coordinates")
for i in range(5):
    print(f"{names2[i]}: {bestpos2[i][0]:11.6f},  {bestpos2[i][1]:11.6f}")
 