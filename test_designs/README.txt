This directory hints at experiments to create physical examples of parts 
and mechanisms that will be needed for the small Babbage Analytical 
Engine.

I am building a sequence of "prototypes" of increasing complexity. All 
the early versions use stepper motors controlled by a microprocessor to 
do shaft lifting and rotation, as a temporary substitute for what must 
eventually become Babbage-like timing and control using cams.

The first prototype has been built and is operational, a second is under 
construction, and a third is anticipated.

Version 1 had:
   - one 2-number 4-digit register stack
   - one each fixed and movable pinions that can transfer and shift
   - two linking pinions to connect each of those to either register number
   - one anticipating carriage that can add and subtract
   - one linking pinion to connect the fixed pinion to the carriage
   - locks on the digit wheels, long pinions, and carriage

 Here's how they were interconnected:

   C  -- F -- FC -- FP == FPC -- \
                    ||            -- A1 or A2
                    MP == MPC -- /

  Double lines represent axles that are always connected, but the FP==MP
  connection can optionally be from MP to the FP above, which does a shift.
  Connecting both FPC and MPC to the same A digit wheel creates a jam.
  
  The canonical test program, which runs well, computes the Fibonacci series.
  See the video at https://youtu.be/I2eggg87dSU.

Version 2 has all of that and adds:
   - a Store with two 2-number digit stacks, so four memory locations
   - a rack for connecting the Store to the Mill
   - a rack-restoring pinion to return the rack to the home position, and
     optionally rewrite the number just read and set to zero
   - a linking pinion to connect the rack to the movable pinion
   - two 20-digit general-purpose counters that can be linked to each other
   - one single-position sign wheel that receives and transmits the sign wheel
     of Store variables
   - an optional reversing gear between the long pinion and the carriages
   - a "running up" lever at the top of the carriage to detect overflows
   - perhaps, since we've reduced the cage height from 2.3" to 2", there will
     be space for 5 digits in all the mechanisms instead of 4.
     
   Preliminary images and incomplete files for the program that runs the stepper
   motors is in the version2 directory.

Version 3 will have all of that and add:
   - a second set of the 2-number register stack, fixed and movable long pinions,
     and anticipating carriage
   - a third set of the 2-number register stack, and fixed and movable long pinions,
     but not a third anticipating carriage.
   - four more Store stacks, for a total of six stacks (12 numbers)
   
   That configuration is essentially the Plan 27 layout, with some performance-enhancing
   features removed. It will be sufficient to do multiplication and division, and all 
   the user-level instructions we propose to implement.
   
   After that comes: card readers, microcode barrels, and control sequencing.

Len Shustek
2 Nov 2025
