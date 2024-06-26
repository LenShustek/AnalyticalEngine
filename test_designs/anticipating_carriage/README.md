# Anticipating Carriage tests

One of the inventions that Babbage was most proud of was his
"anticipating carriage", which does the propagation of carries
in a short time that is independent of the number of consecutive
cascading 9's.  Over a period of decades he produced 88 different
designs for it, so we have many to choose from or be inspired by.

This is a blog-like record of design ideas and sketches for it, in reverse chronological order.

## 4 April 2024

The parts have now been made and the carriage tester prototype is assembled; see carriage v2 tester.jpg. Now I can begin debugging.

I'm not optimistic.

## 10 Mar 2024

The prototype for testing the anticipating carriage continues to develop. 

There were some side roads leading to dead ends that wasted several days. I thought the carry warning could be simplified by putting the carriage digit wheel gear adjacent to the carry nib disc, but that doesn't work because when the carry sector engages, it interferes with the movable wire. Then I tried doing away with the big intermediate carry pinion by using the regular fixed long pinion instead, but it too causes interference. So it's basically back to the 29 Feb 2024 design.

What is shown here as V2 is a tester for it that implements addition and subtraction to the anticipating carriage, optionally making a copy of the input onto the second number of the input digit wheel stack. That will be enough mechanism to run a program to compute Fibonacci numbers. The prototype also implements, just for testing in anticipation of what will be needed for multiplication and division, power-of-10 shifting in both directions.

I've started to build the frame for the prototype, and to wire up the electronics for the stepper motors using multiple copies of a PC board I had designed several years ago for automating our weaving loom, https://github.com/LenShustek/loom. But the detailed mechanical design needs to be studied a little more before it's time to start 3D printing the parts. If anyone sees a problem please let me know quickly.


## 29 Feb 2024

I continue to develop the design for the anticipating carriage. See the latest drawing in carriage v1.1.jpg.

In order to do subtraction I came up with a tweak that Babbage apparently never used: rather than having two different numberings on the wheel to change the chain-of-9 detector using the fixed and movable wires into a chain-of-0 detector, I move the detector itself to either the 9-position of the movable wire or the 10-position. This results in a considerable simplification.

There may well be some fatal flaw in this scheme, because surely Babbage would otherwise have proposed it. But so far neither Tim Robinson nor I have discovered the problem. 

I may be ready to build a prototype to try it out. The idea is to build a frame, perhaps 12"W x 18"L x 12"H, to contain the 19th-century mechanism shown in the drawing. Below that will be the 21st-century magic that animates it for testing: 7 stepper motors to provide shaft rotary motions, and 5 to provide shaft lifting motions using lead screws. Plus 12 stepper motor drivers, a microprocessor, and a sprinkling of software.

## 8 Feb 2024

This first experiment (V1) is just an cartoon sketch to see if
I've got the basic idea right. I used Solidworks to draw a 4-digit
stack and some of the required parts. The video is an *animation*, 
not a *simulation*; it doesn't recognize interference or make motion
inferences based on contact between parts.

The animation shows a number (just a single units digit) being added from the stack on the right to the carriage in the center. The actual numerals on the digit wheels are missing, and the relative position of the carry warning tab to the moveable "wire" (actually a slug) that detects the 9 position is arbitrary.

The animation demonstrates a particularly hard case:
- the units digit on the bottom rotates from 9 to 0 and beyond, so it must cause a carry to the tens
- the tens digit is at 9, so it must propagate the carry to the hundreds using the moveable wire
- the hundreds is at 8, so it doesn't propagate, but it must avoid interference of its moveable wire with the carry warning from below

The timing isn't as good as as Babbage achieved:

1. 9 time units for "giving off" of the value on the right stack, which moves the carry warning at the units level into position
2. 1 time unit for raising the carry chain and the pinions that need to increment digit wheels
3. 1 time unit for locking the pinions
4. 1 time unit for lowering the carry chain to avoid interference
5. 1 time unit for rotating the pinions to move the wheels by one digit

We need to do better.

Not shown is the return to the home position, or how to deal with subtraction. There's plenty more to do.

