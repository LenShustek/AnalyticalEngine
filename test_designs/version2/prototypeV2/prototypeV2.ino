#include "prototype.h"
#include "EEPROM.h"
/***********************************************************************************************************

   -----  Control program for the Analytical Engine prototype  -----

   The AE prototype is a testbed for some Babbage-designed 19th century mechanisms.
   It is driven for testing from the level below by 21st century stepper motors and
   electronics. This is the control program for its Teensy 4.0 microcomputer.


   There are three version of the "prototype", in addition to some special testers.

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

   Version 3 will have all of that and add:
      - a second set of the 2-number register stack, fixed and movable long pinions,
        and anticipating carriage
      - a third set of the 2-number register stack, and fixed and movable long pinions,
        but not a third anticipating carriage.
      - four more Store stacks, for a total of six stacks (12 numbers)
   This configuration is essentially the Plan 27 layout. It will be sufficient to do
   multiplication and division, and all the user-level instructions we propose.

   The motors are controlled by the microcomputer as directed by motion commands entered
   on a USB serial console. All commands take one unit of "timeunit" milliseconds by default,
   except that "lock" and "unlock" takes half that. The defaults can be overridden with the
   "time" command modifier.

   This version of the software corresponds to Version 2 described above.

   The serial console should be set for "newline" as the ending character.
   We use the Coolterm terminal emulator because the Arduino Serial Monitor
   doesn't provide for reading individual characters until Enter has been hit.
   Use these Options: "Enter key is LF", and "Handle BS and DEL".

   Several commands can be on one line, separated by semicolons.
   Hitting "Enter" on an empty line repeats the last command.
   Hitting "backspace" on an empty line repeats the next-to-last command.
*/
const char* help[] = { // COMMANDS
   // These are the 19th century engine action commands
   " lock|unlock An[top|bot] | MPn | FPn | R", // move a gear lock in 1/2 timeunit
   " lock1 MPn|FPn",                          // lock only the top (MP) or bottom (FP) pinion
   " mesh FPn|MPn An[top|bot]",               // create the link from a fixed or movable pinion to an A digit wheel
   " unmesh FPn|MPn An",                      // break that link
   " mesh Sn|RR top|bot rack|finger",         // mesh a Store or Rack Restorer wheel top or bottom with rack only, or rack and finger
   " unmesh Sn|RR",                           // unmesh and lock the store wheel
   " mesh RPn  An{top|bot} | MPn",            // mesh the rack to an A digit wheel, or just to MP2
   " mesh FCn | REVn",                        // create an FP to carriage link straight, or with reversal
   " unmesh RPn | FCn | REVn",                // break the specified link
   " finger An{top|bot} | Fn",                // make the giving-off finger engage with the named digit wheel
   " nofinger An|Fn",                         // make the giving-off finger not engaged
   " shift MPn [up|down]",                    // make the movable long pinons shift, or not
   " giveoff An|Fn|Sn|RR [degrees] [reverse]",// rotate the digit wheel down (or up) one digit, or an arbitrary degrees
   " setcarry Fn 0|9",                        // carry chain position for 0's or 9's
   " carrywarn Fn up|down|reset|return",      // carry warning arm lift, or rotate to reset the carry warning arms
   " carry Fn add|sub|home",                  // rotate the carry sectors to add or subtract one, and return to home position
   " keepers Fn up|mid|down|top|bottom",      // lift or rotate the carry sector keepers into position
   "+optional: delay | time n m",             // for movements: delay to 2nd half, or to time relative to 0..99

   // these are the 21st century driver commands
   " [run]|step {%s} [parms]",                  // run or single-step a script, with #n replaced with the nth parm
   "   read|write s top|bot a top|bot",         //    read or write between Store s and Mill a
   "   readonly s top|bot",                     //    read Store s
   "   restore | revrestore",                   //    restore the rack after writing, or reverse restore after reading
   "   rewrite s top|bot",                      //    reverse restore the rack after reading, and rewrite the value
   "   zeroF n [calibrate]",                    //    zero (or maybe calibrate) a carriage
   "   zeroA|zeroS n top|bot [calibrate]",      //    zero (or maybe calibrate) a Mill or Store digit wheel
   "   zeroRR top|bot [calibrate]",             //    zero (or maybe calibrate) the rack restorer
   " repeat [n] <commands>",                    // repeat a list of commands until count or ESC or space

   // All those are remembered and can be repeated with Enter or Backspace.
   // The following state commands are not remembered:
   " home | state | reset | pause [ms] | bell | restart",  // move to initial position, show state, reset internal state, pause script n msec, sound bell, restart processor
   " timeunit [ms] | tu | debug [n]",     // set parameters
   " switches | motors",                  // monitor for changes in the switches; show motor assignments
   " help | ?",                           // show help
   " off|on [<axle>|all]",                // motor power control for either everything or a named axle motor
   " rot|lift <axle> <amount>",           // primitive lift in mils, or rotation in degrees
   " calibrate <axle> <degrees>",         // force calibration of digit wheel stack
   NULL };
/*
   When movements are in progress:
     - hitting ESC does an emergency abort with no further motion
     - hitting any other character does an abort and then a "home" command

   Information about the digit wheel rotational position sensors that has been deduced by
   "calibrate" commands is recorded in non-volatile EEPROM memory and loaded on startup.

   Except for the rotational position of the finger axles that is sensed by a microswitch and
   can be initialized with the "zero" command, the machine cannot sense its current physical
   state. It assumes the following initial conditions on startup or after a "reset" or "home"
   command is issued:

      lock F; lock A1; lock A2; lock FP; lock MP;
      unmesh FC; unmesh FPC; unmesh MPC
      nofinger F; nofinger A
      setcarry 9; carrywarn down;
      keepers top; keepers down
      //carry sectors rotated towards F
      //carry warning arms set to "not warned"
      ...MORE TBD...

   Set the reference voltage on the DRV8825 driver boards to current limit as follows:
     NEMA 17 60mm long: max 2.1A, set to 0.8V for 1.6A
     NEMA 11 28mm long: max 0.8A, set to 0.3V for 0.6A
     NEMA 8  39mm long: max 0.8A, set to 0.3V for 0.6A
     NEMA 8  27mm long: max 0.2A, set to 0.1V for 0.2A

   To further limit torque on certain motors, lower the reference voltage, or increase torque with higher voltage.

   We use quarter-step micro-stepping, so the holding torque is reduced to about 38%
   compared to full stepping. But apparently pull-out torque is not; see these:
   See https://embeddedtronicsblog.wordpress.com/2020/09/03/torque-vs-microstepping/
   and https://www.rototron.info/wp-content/uploads/PiStepper_Microstepping_WP.pdf.

   ---- change log ----
   14 Mar 2024, L. Shustek, started, compatible with Teensy 3.5, 3.6, or 4.1.
   19 May 2024, L. Shustek, various changes and additions
   17 Jun 2024, L. Shustek, add carriage wire return motors
   26 Sep 2024, L. Shustek, add fixed long pinion lock, and option for small prototype tester
    1 Oct 2024, L. Shustek, add partial time unit operations so that 2 consecutive locks can occur in 1 unit
   19 Oct 2024, L. Shustek, change to new bidirectional carry warning arms that can lower the carry sector lifters;
                            add half cycle unlocks; change some command terminology
   27 Oct 2024, L. Shustek, add carry sector lifter return arms rotated by a new motor
    5 Nov 2024, L. Shustek, remove that new motor for the new carry lifter design, so we're back to 17
    9 Dec 2024, L. Shustek, implement "time n m" to allow movements to span multiple time units
    5 Feb 2025, L. Shustek, add "nolock" for weak locking of F locks
   16 Apr 2025, L. Shustek, Support the new version 2 motor control boards.
                            Implement exact motor movement by accumulating fractional microstep deficits.
                            Support the store tester jig.
   31 Jul 2025, L. Shustek, Retrofit to work with add/sub (Fibonacci) prototype again.
   19 Aug 2025, L. Shustek, Major change for store/add/sub prototype. Divide into multiple modules.
   31 Aug 2025, L. Shustek, Allow parallel execution of scripts; add script substitutable parameters
    2 Nov 2025, L. Shustek, Allow some motors to round down movements to full steps to allow powering down.

   *************************************************************************************************************/

struct config_t  // the configuration record written to non-volatile EEPROM memory
   config = { 0 };

unsigned long timeunit_usec = DEFAULT_TIMEUNIT_MSEC * 1000L;  // to move one digit, or lift, or unlock, etc.

int debug = 1;              // debug level from 0 to 5
int motors_queued = 0;      // how many motors are currently queued up to move
bool got_error = false;     // was an error generated during this action?
bool script_step = false;   // should we pause at each script command?
int cyclenum = 0;

void assert(bool test, const char* msg1, const char* msg2) {
   if (!test) {
      Serial.printf("*** ASSERTION FAILED: %s %s\n", msg1, msg2);
      while (1); } }
void assert(bool test, const char* msg) {
   assert(test, msg, ""); }
void assert(bool test, const char*msg, int value) {
   if (!test) {
      char number[20];
      sprintf(number, "%d", value);
      assert(false, msg, number); } }

void read_config(void) {
   for (unsigned i = 0; i < sizeof(config); ++i)
      ((char*)&config)[i] = EEPROM.read(i);
   if (strncmp(config.id, CONFIG_ID, sizeof(config.id)) != 0)
      Serial.printf("*** no config block in EEPROM\n");
   else for (int motornum = 0; motornum < NUM_MOTORS; ++motornum)
         if (config.finger_zero_degrees[motornum].degrees != -1) { // undefined is 0xff!
            struct motord_t *pmd = motor_num_to_descr[motornum];
            assert(pmd, "undeclared motor: ", motornum);
            Serial.printf("digit wheel %s (%s) is calibrated to %d degrees\n",
                          pmd->axle_name, pmd->axle_descr,
                          config.finger_zero_degrees[motornum].degrees); } }

void write_config(void) {
   strcpy(config.id, CONFIG_ID);
   for (unsigned i = 0; i < sizeof(config); ++i)
      EEPROM.write(i, ((char*)&config)[i]);
   Serial.printf("config block written\n"); }

void setup(void) {
   initialize_iopins();  // disable all motor controllers quickly
   Serial.begin(115200);
   delay(500);
   while (!Serial.available())
      ;  // wait for terminal emulator to connect and user to hit Enter
   Serial.printf("*** AE prototype tester ***\nThe timeunit is %d msec, debug is %d.\n", timeunit_usec / 1000L, debug);
   initialize_motors();
   read_config(); }

//****  the main loop

void loop(void) {

   getstring(cmdline, sizeof(cmdline));  // get and parse commands
   got_error = script_step = false;
   cyclenum = 0;
   execute_commands(cmdline);
   //if (!got_error) do_movements(timeunit_usec);  // do any queued "rot" and "lift" movements
   if (cyclenum > 1) {
      unsigned msec = (cyclenum * timeunit_usec) / 1000;
      Serial.printf("%u time units, %u.%03u seconds\n", cyclenum, msec / 1000, msec % 1000); } }
