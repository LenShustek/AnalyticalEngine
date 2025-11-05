#include "prototype.h"

#define MIN_uSTEP_TIME_USEC 175     // minimum time between microsteps for reliable operation
// 1000 RPM max * 800 usteps/rev * min/60 sec = 75 usec, but 100 usec doesn't work!
#define MOVE_TICK_USEC 50           // how often to wait between check for something to do when moving
#define STEPS_PER_ROTATION 200      // 1.8 degree step angle for Nema 11 2-phase stepper motor
#define TIGHTEN_LOCK_DEGREES 2      // force the rotary lock to tighten by these many degrees

/* The default for lifters is no gearing, ie 1:1, because most of them drive a leadscrew directly.
   The default for rotators is the "5:1" gearmotor sold by StepperOnline, also described as "5.18:1".
   The actual ratio is 5+2/11, or 5.1818181818, which we rationalize as 57/11.
   For more info, see the comments in queue_movement(). */
#define GEARMOTOR_BIG 57        // 57:11 gearing in the gearmotor
#define GEARMOTOR_SMALL 11
#define MILL_DIGIT_GEAR_BIG 2   // 32:16 (2:1) gearing in the Mill
#define MILL_DIGIT_GEAR_SMALL 1
#define STORE_DIGIT_GEAR_BIG 25 // 50:16 (25:8) gearing in the Store
#define STORE_DIGIT_GEAR_SMALL 8

//**** define I/O pins

#define MOTOR_BDSEL_2A 7   // board select: make one of 2A/2B low and one of
#define MOTOR_BDSEL_2B 8   // 3A/3B/3C low to select one of six identical motor 
#define MOTOR_BDSEL_3A 3   // control boards that are daisy-chained together.
#define MOTOR_BDSEL_3B 4   // See the 1979 patent 4,253,087, "Self-assigning address
#define MOTOR_BDSEL_3C 5   // system", by Harry Saal of Nestar Systems

#define MUXA 17         // 4-to-16 multiplexer controls for addressing the motors
#define MUXB 16         //   on the currently-selected board,
#define MUXC 15         //   or for reading one of the 16 global switch inputs
#define MUXD 14         //  
#define STEPnotENB 19   // whether selecting the board steps the motor selected by the ABCD
//                      //   multiplexer, or sets the power on/off status of that motor
#define MOTOR_ENB 22    //   depending on the state of MOTOR_ENB 
#define MOTOR_ON LOW
#define MOTOR_OFF HIGH
#define SWITCH_INPUT 23 // input: the switch selected by the A/B/C/D mux controls 

#define MOTOR_FAULT 20  // active low input: a motor fault was detected
#define MOTOR_DIR 21    // direction control for all motors
#define FAN_ON 11       // turn on the cooling fans

#define HIGH 1
#define LOW 0

int num_declared = NUM_MOTORS, num_defined = 0, num_assigned = 0;
struct motor_select_t { // map from motor number 0 to 95 to I/O pins needed to select it
   int bd_grp2;     // which of MOTOR_BDSEL_2A/2B to assert to select the board
   int bd_grp3;     // which of MOTOR_BDSEL_3A/3B/3C to assert to select the board
   int motorpos;    // which motor position on that board labeled from 0 to 15
}  motor_selects[NUM_MOTORS];
int motorboards[6][2] = { // outputs that select each of the six boards
   {MOTOR_BDSEL_2A, MOTOR_BDSEL_3A }, // The 0th board, with the Teensy processor.
   {MOTOR_BDSEL_2B, MOTOR_BDSEL_3B }, // The remaining boards in the order of
   {MOTOR_BDSEL_2A, MOTOR_BDSEL_3C }, // the daisy chained cables, connected from
   {MOTOR_BDSEL_2B, MOTOR_BDSEL_3A }, // the right connector of one board to the
   {MOTOR_BDSEL_2A, MOTOR_BDSEL_3B }, // left connector of the next board.
   {MOTOR_BDSEL_2B, MOTOR_BDSEL_3C } };
void setmotor(enum motornum_t motornum /*0 to NUM_MOTORS-1*/, int boardnum /*1 to 6*/, int motorposn /*1 to 16*/) {
   struct motord_t* pmd = motor_num_to_descr[motornum];
   if (!pmd) Serial.printf("BAD: motornum %d, boardnum %d, motorposn %d\n", motornum, boardnum, motorposn); //TEMP
   assert(pmd, "bad motor number in setmotor:", motornum);
   assert(!pmd->assigned, "motor already assigned:", pmd->axle_name);
   motor_selects[motornum].bd_grp2 = motorboards[boardnum - 1][0];
   motor_selects[motornum].bd_grp3 = motorboards[boardnum - 1][1];
   motor_selects[motornum].motorpos = motorposn - 1;
   pmd->assigned = true;
   pmd->board_number = boardnum;
   pmd->board_position = motorposn;
   ++num_assigned; }

/* Creating motors is a three-step process:
   (1) Motors are *declared* in prototype.h
   (2) Motors are *defined* here by allocating and initializing a motor descriptor for them.
*/
struct motord_t motor_descriptors[] = {  // an unordered liset of descriptors for defined motors
   //  put longer names first so they get scanned first in case later ones are prefixes
   //  default gears are none (1:1)
   { FP2K_R, ROTATE, "fp2k", "fixed long pinion 2 lock", GEARMOTOR_BIG, GEARMOTOR_SMALL /*TEMP ,.always_on = true*/ },
   { MP2K_R, ROTATE, "mp2k", "movable long pinion 2 lock", GEARMOTOR_BIG, GEARMOTOR_SMALL /*TEMP .always_on = true*/ },
   { P21_L, LIFT, "p21", "movable long pinion 2 connector to A2 lift" },
   { P22_L, LIFT, "p22", "fixed long pinion 2 connector to A2 lift" },
   { FC2_L, LIFT, "fc2", "carriage 2 connector" },
   { REV2_L, LIFT, "rev2", "carriage 2 reversing pinion" },
   { MP2_L, LIFT, "mp2", "movable long pinion 2 lift" },
   { A2K_L, LIFT, "a2k", "A2 lock lift" },
   { A2_L, LIFT, "a2l", "A2 finger lift", GEARMOTOR_BIG, GEARMOTOR_SMALL }, // should remove gearmotor!
   { A2_R, ROTATE, "a2r", "A2 finger rotate", MILL_DIGIT_GEAR_BIG * GEARMOTOR_BIG, MILL_DIGIT_GEAR_SMALL * GEARMOTOR_SMALL, A2_L/*compensating lifter*/}, // should remove gearmotor!
   { F2_L, LIFT, "f2l", "carriage 2 finger lift" },
   { F2_R, ROTATE, "f2r", "carriage 2 finger rotate", MILL_DIGIT_GEAR_BIG, MILL_DIGIT_GEAR_SMALL, F2_L/*compensating lifter*/},
   { CL2_R, ROTATE, "cl2", "carry lifter 2 rotate", GEARMOTOR_BIG, GEARMOTOR_SMALL },
   { CS2_R, ROTATE, "cs2", "carry sector 2 rotate", GEARMOTOR_BIG, GEARMOTOR_SMALL },
   { CW2_L, LIFT, "cw2l", "carry warning 2 lift", GEARMOTOR_BIG, GEARMOTOR_SMALL },
   { CW2_R, ROTATE, "cw2r", "carry warning 2 rotate (for reset)", MILL_DIGIT_GEAR_BIG * GEARMOTOR_BIG, MILL_DIGIT_GEAR_SMALL * GEARMOTOR_SMALL, CW2_L/*compensating lifter*/ },
   { CSK2_L, LIFT, "csk2l", "carry sector keepers 2 lift" },
   { CSK2_R, ROTATE, "csk2r", "carry sector keepers 2 rotation", MILL_DIGIT_GEAR_BIG, MILL_DIGIT_GEAR_SMALL, CSK2_L/*compensating lifter*/ },
   { S1_L, LIFT, "s1l", "store stack 1 lift" },
   { S1_R, ROTATE, "s1r", "store stack 1 rotate", STORE_DIGIT_GEAR_BIG * GEARMOTOR_BIG, STORE_DIGIT_GEAR_SMALL * GEARMOTOR_SMALL, S1_L/*compensating lifter*/ }, // should remove gearmotor!
   { RR_L, LIFT, "rrl", "rack restore lift" },
   { RR_R, ROTATE, "rrr", "rack restore rotate", STORE_DIGIT_GEAR_BIG * GEARMOTOR_BIG, STORE_DIGIT_GEAR_SMALL * GEARMOTOR_SMALL, RR_L/*compensating lifter*/  },
   { RP2_L, LIFT, "rp2", "rack pinion 1 lift" },
   { SIGN_L, LIFT, "signl", "sign lift" },
   { SIGN_R, ROTATE, "signr", "sign rotate", GEARMOTOR_BIG, GEARMOTOR_SMALL },
   { CTR1_L, LIFT, "ctr1l", "counter 1 lift" },
   { CTR1_R, ROTATE, "ctr1r", "counter 1 rotate", GEARMOTOR_BIG, GEARMOTOR_SMALL },
   { CTR2_L, LIFT, "ctr2l", "counter 2 lift" },
   { CTR2_R, ROTATE, "ctr2r", "counter 2 rotate", GEARMOTOR_BIG, GEARMOTOR_SMALL },
   { RK_L, LIFT, "rk", "rack lock" },
   { TEST_R, ROTATE, "test", "test motor" },
   { -1 } };

/* (3) Motors are *assigned* here to specific controllers on the daisy-chained motor control boards,
       at which point they are usable.
*/
void assign_motors(void) { // assign the physical location of the driver for each motor
   // Note that we number the boards from 1 to 6 and the motors on the board from 1 to 16
   // so that it matches the silkscreen on the boards. Internally in the code the arrays use 0-origin.
   // In these setmotor calls, the first number is the board (1 to 6) and the second is the motor number (1 to 16)
   setmotor(S1_L, 1, 1); // store 1 lift
   setmotor(S1_R, 1, 2); // store 1 rotate
   setmotor(RP2_L, 1, 3); // rack pinion 2 lift
   setmotor(P21_L, 1, 4); // movable long pinion connector 2 lift
   setmotor(MP2_L, 1, 5); // movable long pinion 2 lift
   setmotor(A2_L, 1, 6);   // A2 digit stack lift    (fingers)
   setmotor(A2_R, 1, 7);   // A2 digit stack rotate  (fingers)
   setmotor(A2K_L, 1, 8);  // A2 digit stack lock lift
   setmotor(SIGN_L, 1, 9); // fixed long pinion 2 lock rotate
   setmotor(SIGN_R, 1, 10); // fixed long pinion 2 lock rotate
   setmotor(FP2K_R, 1, 11); // fixed long pinion 2 lock rotate
   setmotor(MP2K_R, 1, 12); // movable long pinion 2 lock rotate
   setmotor(RK_L, 1, 13);  // rack lock lift
   setmotor(RR_L, 1, 14); // rack restorer lift
   setmotor(RR_R, 1, 15);  // rack restorer rotate (fingers)
   setmotor(P22_L, 1, 16); // fixed long pinion connector 2 lift

   setmotor(REV2_L, 2, 1); // reversing gear lift
   setmotor(FC2_L, 2, 2); // carriage wheel connector lift   DOESN'T TURN OFF??
   setmotor(F2_L, 2, 3); // carriage wheel finger lift
   setmotor(F2_R, 2, 4); // carriage wheel finger rotate
   setmotor(CL2_R, 2, 5); // carry lifter rotate
   setmotor(CS2_R, 2, 6); // carry sector rotate
   setmotor(CW2_L, 2, 7);  // carry warning arms lift
   setmotor(CW2_R, 2, 8);  // carry warning arms rotate
   //setmotor(??, 2, 9);  // broken socket? driver was ok!
   setmotor(CSK2_R, 2, 10);  // carry sector keepers rotate
   setmotor(CTR1_L, 2, 11);  // counter 1 lift
   setmotor(CTR1_R, 2, 12);  // counter 1 rotate
   setmotor(CTR2_L, 2, 13);  // counter 2 lift
   setmotor(CTR2_R, 2, 14);  // counter 2 rotate
   setmotor(CSK2_L, 2, 15);    // carry sector keepers lift
   setmotor(TEST_R, 2, 16); } // test motor
struct motord_t* motor_num_to_descr[NUM_MOTORS]  // a map from motor number to motor descriptor
      = { 0 };

void pinhigh(int pin) {
   digitalWrite(pin, HIGH);
   pinMode(pin, OUTPUT); }

void setmux(int posn) { // set the multiplexor control based on a 0..15 position
   digitalWrite(MUXA, posn & 1 ? HIGH : LOW);
   digitalWrite(MUXB, posn & 2 ? HIGH : LOW);
   digitalWrite(MUXC, posn & 4 ? HIGH : LOW);
   digitalWrite(MUXD, posn & 8 ? HIGH : LOW); }

void initialize_iopins(void) {
   pinMode(MOTOR_FAULT, INPUT_PULLUP);
   pinMode(SWITCH_INPUT, INPUT_PULLUP);
   pinMode(FAN_ON, OUTPUT);
   static int output_pins[] = {  // intitialize most output pins to high
      MOTOR_DIR, MOTOR_ENB, STEPnotENB,
      MUXA, MUXB, MUXC, MUXD,
      MOTOR_BDSEL_2A, MOTOR_BDSEL_2B, MOTOR_BDSEL_3A, MOTOR_BDSEL_3B, MOTOR_BDSEL_3C };
   for (unsigned int pin = 0; pin < sizeof(output_pins) / sizeof(output_pins[0]); ++pin) {
      digitalWrite(output_pins[pin], HIGH);
      pinMode(output_pins[pin], OUTPUT); }
   // Disable all possible motor controllers that might be populated even though there
   // might not be a motor assigned to them, because they will draw power.
   digitalWrite(STEPnotENB, LOW); // "we are setting ENB for the motor, not stepping"
   digitalWrite(MOTOR_ENB, MOTOR_OFF); // the value to set into ENB
   for (int posn = 0; posn < 16; ++posn) { // for each of 16 positions on a board
      setmux(posn); // select one of 16 motor controllers
      for (int board = 0; board < 6; ++board) { // for each of 6 possible boards
         delayMicroseconds(1); // the CD74HC259 addressable latch spec says 120 nsec minimum setup time
         digitalWrite(motorboards[board][0], LOW);  // assert one of 2 and one of 3 to select
         digitalWrite(motorboards[board][1], LOW);  // the motor board and clock the latch
         delayMicroseconds(1); // the spec says 100 nsec minimum pulse time
         digitalWrite(motorboards[board][0], HIGH);  // now deselect it
         digitalWrite(motorboards[board][1], HIGH); } } }


void initialize_motors(void) {
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      // create a map from motor number to motor descriptor
      int motornum = pmd->motor_number;
      if (motornum != NM) {
         if (motor_num_to_descr[motornum]) Serial.printf("ERROR: motor %u is duplicated!\n", motornum);
         //Serial.printf("motor %d connected to %s\n", motornum, pmd->axle_name);
         motor_num_to_descr[motornum] = pmd;
         ++num_defined;
         // adjust defaults in the motor descriptor
         pmd->motor_state = OFF;
         if (pmd->gear_big == 0) { // if the gear ratio is not already set
            pmd->gear_big = 1; pmd->gear_small = 1; } // assume 1:1
         // special cases we need to tweak
         //TEMP if (motornum == FP2K_R || motornum == MP2K_R) // some motors need to stay powered on to keep locking
         //TEMP   pmd->always_on = true;
         if (motornum == RK_L) pmd->full_steps = true; // round to full steps to allow powering off between movements
      } }
   assign_motors();   // assign the addressing for the motors actually plugged in
   Serial.printf("%d motors were declared, %d were defined, and %d were assigned board positions\n",
                 num_declared, num_defined, num_assigned); }

void show_motors(void) {
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd)
      if (pmd->assigned) {
         int motornum = pmd->motor_number;
         if (motornum != NM) Serial.printf("  motor %d (%s, %s) is position %d on board %d, %s, step offset %d\n",
                                              motornum, pmd->axle_name, pmd->axle_descr,
                                              motor_selects[motornum].motorpos + 1, pmd->board_number,
                                              pmd->motor_state == ON ? "ON" : "OFF", pmd->microstep_offset); } }

bool locked(int motor_num, bool warn) {  // is a lock in place?
   if (motor_num != NM) {
      struct motord_t* md = motor_num_to_descr[motor_num];
      if (md && md->current_position == 0) {
         if (warn) Serial.printf("ERROR: %s is locked!\n", md->axle_name);
         return true; } }
   return false; }

void power_motor(struct motord_t* pmd, enum motor_state_t onoff, bool forceoff) { // power a motor on or off
   // by setting one of the 16 addressable latches on the board that motor is connected to
   assert(pmd && pmd->assigned, "unassigned motor in power_motor:", pmd ? pmd->axle_name : "");
   if (pmd->motor_state != onoff) { // current state is different
      int motornum = pmd->motor_number;
      if (onoff == OFF) { // check conditions for denying power off
         if (!forceoff && (pmd->always_on || pmd->temp_on || pmd->microstep_offset != 0)) { // can't turn off a motor between full-step positions
            if (debug >= 4 && pmd->microstep_offset != 0) Serial.printf("  motor %d (%s on board %d position %d) not at full step so left on\n",
                     motornum, pmd->axle_name, pmd->board_number, pmd->board_position);
            return; } }
      else /*ON*/ pmd->microstep_offset = 0;  // microstep offset goes back to zero when powering on
      setmux(motor_selects[motornum].motorpos);  // set A/B/C/D to select the motor on the board
      digitalWrite(STEPnotENB, LOW); // "we are setting ENB for the motor, not stepping"
      digitalWrite(MOTOR_ENB, onoff == ON ? MOTOR_ON : MOTOR_OFF); // the value to set into ENB
      delayMicroseconds(1); // the CD74HC259 addressable latch spec says 120 nsec minimum setup time
      digitalWrite(motor_selects[motornum].bd_grp2, LOW);  // assert one of 2 and one of 3 to select
      digitalWrite(motor_selects[motornum].bd_grp3, LOW);  // the motor board and clock the latch
      delayMicroseconds(1); // the spec says 100 nsec minimum pulse time
      digitalWrite(motor_selects[motornum].bd_grp2, HIGH);  // now deselect it
      digitalWrite(motor_selects[motornum].bd_grp3, HIGH);
      pmd->motor_state = onoff;
      if (debug >= 4)  Serial.printf("  motor %d (%s on board %d position %d) turned %s\n",
                                        motornum, pmd->axle_name, pmd->board_number, pmd->board_position, onoff == ON ? "on" : "off"); } }

void power_motors(enum motor_state_t onoff, bool all) { // power all motors; "all" ignores always-on motor status
   if (debug >= 5) Serial.printf("powering %s motors %s\n", all ? "all" : "some", onoff == ON ? "on" : "off");
   got_error = false;
   digitalWrite(FAN_ON, onoff == ON ? HIGH : LOW);
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) { // all defined motors
      if (pmd->assigned) { // we have assigned its position
         if (onoff == OFF) power_motor(pmd, OFF, all); // if "all", even power off "always on" motors
         else { //ON
            if (all || pmd->always_on) { // if not "all", only "always on" motor get turned on, other are turned off
               power_motor(pmd, ON);
               //TEMP queue_movement(pmd, ROTATE, TIGHTEN_LOCK_DEGREES); //TEMP BUG: might be wrong direction
            }
            else power_motor(pmd, OFF); } } }
   //TEMP causes infinite calling of do_movements: if (!got_error) do_movements(timeunit_usec);
}

void step_motor(struct motord_t* pmd) {  // step a motor
   int motornum = pmd->motor_number;
   digitalWrite(MOTOR_DIR, pmd->clockwise);
   if (pmd->clockwise) { // keep track of how much off the full-step position we are
      if (++pmd->microstep_offset >= uSTEPS_PER_STEP) pmd->microstep_offset = 0; }
   else if (--pmd->microstep_offset < 0) pmd->microstep_offset = uSTEPS_PER_STEP - 1;
   setmux(motor_selects[motornum].motorpos); // set A/B/C/D to select the motor on the board
   digitalWrite(STEPnotENB, HIGH); // "we are stepping, not setting ENB for the motor"
   delayMicroseconds(1);
   digitalWrite(motor_selects[motornum].bd_grp2, LOW);  // assert one of 2 and one of 3 to select
   digitalWrite(motor_selects[motornum].bd_grp3, LOW);  //  the motor board and assert the STEP
   delayMicroseconds(3);   // TI DRV8825 stepper motor controller spec: pulse min 1.9 usec high
   digitalWrite(motor_selects[motornum].bd_grp2, HIGH);  // stop board select
   digitalWrite(motor_selects[motornum].bd_grp3, HIGH);
   if (debug >= 6) Serial.printf("motor %d (%s) stepped\n",
                                    motornum, motor_num_to_descr[motornum]->axle_name); }

int wait_for_char(void) {
   flush_input();
   while (Serial.available() == 0);
   int key = Serial.read();
   if (key == ESC) {
      Serial.println("\n...aborted");
      clear_movements(); }
   return key; }

bool check_abort(void) {  // check for conditions that abort the current movements
   if (Serial.available()) {
      char chr = Serial.read();
      if (chr == DEL) {  //  (1) DEL from the keyboard
         clear_movements();
         Serial.println("...stop and reset to neutral");
         do_homescript();  // return everything to home position
         return true; }
      if (chr == ESC) {  // (2) ESC from the keyboard
         clear_movements();
         Serial.println("...immediate abort");
         return true; } }
   if (digitalRead(MOTOR_FAULT) == LOW) {  // (3) a motor fault
      error("motor fault", "");
      return true; }
   return false; }

void do_test(void) {
   Serial.println("enter chars, ESC to exit");
   while (1)
      if (Serial.available()) {
         char chr = Serial.read();
         if (chr == ESC) break;
         Serial.printf("%02X\n", chr); }
   do {

   }
   while (!check_abort()); }

//****  movement queuing and execution

bool do_movements(unsigned long duration_usec) {
   // do all the movements queued up for this time unit, and return true if everything worked ok
   if (motors_queued == 0) return true;
   if (debug >= 2) {
      Serial.printf("doing movements for %d motors:", motors_queued);
      for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd)
         if (pmd->move_queued) Serial.printf(" %s", pmd->axle_name);
      Serial.println(); }
   if (check_abort()) {
      Serial.println("ABORTED"); //temp
      motors_queued = 0;
      got_error = true;
      return false; }
   power_motors(ON);  // enable the always-on motors, maybe tightening locks that are in

   //*** 1. precompute some variables for motors to be moved, and turn them on
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd)
      if (pmd->move_queued) {   // look at motors that have queued moves
         power_motor(pmd, ON); // turn it on if off
         unsigned end_pct_now = pmd->end_pct;
         if (end_pct_now > 99) end_pct_now = 99; // only do steps in this time unit
         pmd->ending_ustep = (pmd->usteps_needed * (end_pct_now - pmd->start_pct + 1)) / (pmd->end_pct - pmd->start_pct + 1);
         pmd->step_delta_time = (((end_pct_now - pmd->start_pct + 1) * duration_usec) / 100) / pmd->ending_ustep;
         pmd->start_time = (duration_usec * pmd->start_pct) / 100;
         pmd->usteps_done = 0;
         pmd->last_ustep_time_usec = 0;
         pmd->moving_now = true;
         if (debug >= 4) Serial.printf("  motor %s start time %u, delta %u, ending step %u of %u\n",
                                          pmd->axle_name, pmd->start_time, pmd->step_delta_time, pmd->ending_ustep, pmd->usteps_needed); }
   int motors_moving = motors_queued; // start all queued motors moving
   //if (debug >= 2) Serial.printf("  starting movements for %d motors\n", motors_moving);
   int totalsteps = 0;
   unsigned long timeorigin = micros();
   unsigned timenow = 0;

   //*** 2. do all required movement steps for this time unit, evenly spaced,
   // subject to the minimum microstep time, which might extend the time unit
   while (motors_moving > 0) {  // while there are pending movements
      for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
         if (pmd->moving_now) {  // look at all the motors that are moving
            if (timenow > pmd->start_time) { // we're past the start time for this motor
               unsigned long deltatime = timenow - pmd->last_ustep_time_usec; // time since last step
               if (deltatime > MIN_uSTEP_TIME_USEC && deltatime >= pmd->step_delta_time) {
                  if (debug >= 5) Serial.printf("at time %lu axle %s moves step %d of %u %s\n",
                                                   timenow, pmd->axle_name, pmd->usteps_done + 1, pmd->usteps_needed, pmd->clockwise ? "CW" : "CCW");
                  if (pmd->motor_number == NM) {
                     Serial.printf("axle %s has no motor\n", pmd->axle_name);
                     return false; }
                  step_motor(pmd);
                  ++totalsteps;
                  pmd->last_ustep_time_usec = timenow;
                  if (++pmd->usteps_done >= pmd->ending_ustep) {  // if this motor is done for this time unit
                     if (!pmd->always_on) power_motor(pmd, OFF); // power off if we're allowed to
                     pmd->moving_now = false;
                     --motors_moving; } } } } }
      delayMicroseconds(MOVE_TICK_USEC);
      timenow = micros() - timeorigin; }

   // 3. Prepare to restart motors whose movement extends into the next time unit(s)
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd)
      if (pmd->move_queued) {   // look at motors that had queued moves
         if (pmd->end_pct <= 99) { // this motor is done
            pmd->move_queued = false;
            --motors_queued; }
         else { // this motor has more to do the next time unit
            pmd->usteps_needed -= pmd->ending_ustep; //adjust steps remaining
            pmd->end_pct -= 100; // adjust starting and ending time
            pmd->start_pct = 0;
            if (debug >= 3) Serial.printf("  requeued motor %s for %d microsteps from %d to %d\n",
                                             pmd->axle_name, pmd->usteps_needed,
                                             pmd->start_pct, pmd->end_pct); } }
   if (debug >= 3)   Serial.printf("     did %d steps in %u.%03u msec\n",
                                      totalsteps, timenow / 1000, timenow % 1000);
   return true; }

void queue_movement(  // queue an elemental movement to happen during this time unit
   struct motord_t* pmd, enum movement_t movetype, int distance,
   int start, int end) { // where in the 0..99 range of the time unit it should execute
   // The end can be greater than 99 to indicate that movement spans into subsequent time unit(s).
   if (pmd == NULL) {
      Serial.printf("ERROR: bad call to queue_movement!\n");
      return; }
   if (pmd->move_queued) {
      Serial.printf("WARNING: axle %s is already scheduled to move\n", pmd->axle_name);
      return; }
   pmd->move_queued = true;
   ++motors_queued;
   /*  We do exact computations of microsteps needed, and accumulate the fractional deficits with no rounding errors.

       Rotations are geared through the stepper motor gearbox and/or our external gearset. The motor descriptor
       has the equivalent number of teeth for the driving (small) gear and the driven (big) gear for both
       sets of gears in series.
       For example, the StepperOnline "5:1" gearbox is actually geared 57 to 11, or 5.18181818...
       When in series with our 50/16 gearing in the Store, the effective ratio is 1425/88, or 16.1931818181...
       When in series with our 32/16 gearing in the Mill, the effective ratio is 114/11, or 10.36363636...
       There are 800 microsteps per revolution, so the number of microsteps to move d degrees is
         d degrees * (bigteeth * 800 usteps/rev) / (360 degrees/rev * smallteeth)
       The integer part is used, and the remainder (modulo 360*smallteeth) is the deficit
       we accumulate. When the deficit becomes >= +denominator or <= -denominator, we do + or - one microstep
       and adjust the deficit.

       Lifters are on spiral leadscrews with an 8 mm pitch, and may or may not use a gearmotor. The number of
       microsteps to move m mils (thousandths of an inch) is
         d mils * (25.4mm/in * 800 usteps/rev * bigteeth) / (1000mil/in * 8mm/rev * smallteeth)
         or d * (bigteeth * 254) / (100 * smallteeth)
       As for rotations above, we could do that integer division to compute the number of microsteps and save
       the remainder (modulo 100*smallteeth) for the deficit.

       BUT... lifters are sometimes also called upon to rotate an exact number of degrees, to prevent lifting when
       the axle is rotated. In that case, the number of microsteps to move d degrees is, as for rotators,
         d * (bigteeth * 800) / (360 * smallmeeth)

       In order to have the deficit accumulate exactly when rotations by degrees and lifts by mils are interspersed,
       we use as the denominator of the deficit smallteeth times the least common denominator of 360 and 100, which is 1800.
       So when rotating we multiply the deficit by 1800/100 = 18, and when lifting we multiply the deficit by 1800/360 = 5.

       Got that?
   */
   int numer, denom;
   if (movetype == ROTATE) {  // ROTATE: distance is signed degrees
      numer = distance * pmd->gear_big * uSTEPS_PER_ROTATION;
      denom = 360 * pmd->gear_small;
      pmd->usteps_needed = numer / denom;
      if (pmd->full_steps) // round down to integral number of steps?
         pmd->usteps_needed &= ~(uSTEPS_PER_STEP-1);
      else { // could be a fraction of a microstep
        if (pmd->motor_type == ROTATE) { // normal rotator axis, possibly with gearset
           pmd->deficit += numer % denom; }
        else { // we're rotating a lifter by a specific number of degrees
           pmd->deficit += (numer % denom) * 18;  // 18 = LCD(360,100)/100
           denom *= 18; } } }
   // Note that in C (unlike Python!) the modulus of a negative number is negative, which works out nicely.
   else {  // LIFT: distance is signed mils
      numer = distance * 254 * pmd->gear_big;
      denom = 100 * pmd->gear_small;
      pmd->usteps_needed = numer / denom;
      if (pmd->full_steps) // round down to integral number of steps?
         pmd->usteps_needed &= ~(uSTEPS_PER_STEP-1);
      else { // could be a fraction of a microstep 
         pmd->deficit += (numer % denom) * 5;  // 5 = LCD(360/100)/360
         denom *= 5; } }
   // check how big the accumulated deficit is
   if (pmd->deficit >= denom) { // we just accumulated a full ustep forward
      ++pmd->usteps_needed;
      pmd->deficit -= denom;
      if (debug >= 3) Serial.printf("  ...motor %s used an accumulated step forward\n", pmd->axle_name); }
   else if (pmd->deficit <= -denom) { // we just accumulated a full ustep backward
      --pmd->usteps_needed;
      pmd->deficit += denom;
      if (debug >= 3) Serial.printf("  ...motor %s used an accumulated step backward\n", pmd->axle_name); }
   if (pmd->usteps_needed < 0) { // adjust steps needed to always be positive
      pmd->usteps_needed = -pmd->usteps_needed;
      pmd->clockwise = false; }
   else pmd->clockwise = true;
   if (debug >= 3) Serial.printf("  queued %s of %s motor %s %s for %d %s by %d microsteps from %d to %d, with %d/%d microsteps left over\n",
                                    movetype == ROTATE ? "rotation" : "lift", pmd->motor_type == ROTATE ? "rotator" : "lifter", pmd->axle_name,
                                    pmd->clockwise ? "CW" : "CCW", abs(distance), movetype == ROTATE ? "degrees" : "mils",
                                    pmd->usteps_needed, start, end, pmd->deficit, denom);
   pmd->usteps_done = 0;
   pmd->start_pct = start;
   pmd->end_pct = end;
   if (movetype == ROTATE && pmd->compensating_lifter) // this rotate needs a compensating counter-rotation of the associated lifter
      queue_movement(motor_num_to_descr[pmd->compensating_lifter], ROTATE, -distance); }

void clear_movements(void) {  // cancel all queued movements
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd)
      pmd->move_queued = false;
   motors_queued = 0; }

int read_switch(int switch_number) {
   setmux(switch_number);
   delayMicroseconds(3); // 1 is not enough! (capacitive charging of long wires?)
   return digitalRead(SWITCH_INPUT); }

struct motord_t* move_to_switch(struct fct_move_t /*lifter*/* move) {
   // Rotate the digit wheel (F,A,S,RR) whose lifter is given
   // until it gets to the switch point. Return the axle being rotated.
   static struct { // map from lifter to rotator and switch
      int lift_motor;
      int rotate_motor;
      int switch_number; }
   switchmap[] = {
      {F2_L, F2_R, SW_F2 }, {F3_L, F3_R, SW_F3 },
      {A1_L, A1_R, SW_A1 }, {A2_L, A2_R, SW_A2 }, {A3_L, A3_R, SW_A3 },
      {S1_L, S1_R, SW_S1 }, {S2_L, S2_R, SW_S2 }, {S3_L, S3_R, SW_S3 }, {S4_L, S4_R, SW_S4 }, {S5_L, S5_R, SW_S5 }, {S6_L, S6_R, SW_S6 },
      {RR_L, RR_R, SW_RR }, { -1 } };
   int rotate_motor = -1, switch_number = 0, limit;
   for (int ndx = 0; switchmap[ndx].lift_motor >= 0; ++ndx) // find the right map
      if (switchmap[ndx].lift_motor == move->motor_num) {
         rotate_motor = switchmap[ndx].rotate_motor;
         switch_number = switchmap[ndx].switch_number;
         break; }
   assert(rotate_motor >= 0, "bad lifter in move_to_switch");
   struct motord_t* rotate_axle = motor_num_to_descr[rotate_motor];
   if (debug >= 1) Serial.printf("rotating %s 10 digits\n", rotate_axle->axle_name);
   rotate_axle->temp_on = true; // temporarily force the motor to stay on
   if (rotate_axle->compensating_lifter) // and also the motor of the compensating lifter
      motor_num_to_descr[rotate_axle->compensating_lifter]->temp_on = true;
   queue_movement(rotate_axle, ROTATE, DEGREES_PER_DIGIT * 10);  // rotate 10 digits to ensure the wheel engages with the finger
   if (!do_movements(timeunit_usec * 10)) goto abort;
   limit = 370;
   while (--limit && read_switch(switch_number) == 0) {  // if it's sitting on the switch
      if (debug >= 1) Serial.printf("getting %s off the switch\n", rotate_axle->axle_name);
      queue_movement(rotate_axle, ROTATE, 1 /*degree*/);  // get it off
      if (!do_movements(timeunit_degree_usec)) goto abort; }
   if (!limit) {
      error("switch is always on!", "");
      goto abort; }
   if (debug >= 1) Serial.printf("rotating %s to the switch position\n", rotate_axle->axle_name);
   limit = 370;
   while (--limit && read_switch(switch_number) == 1) {  // now rotate until it just gets on the switch
      // don't need to find the center point, since we always approach it the same way
      queue_movement(rotate_axle, ROTATE, 1 /*degree*/);
      if (!do_movements(timeunit_degree_usec)) goto abort; }
   if (!limit) {
      error("switch is always off!", "");
      goto abort; }
   return rotate_axle;
abort:
   rotate_axle->temp_on = false;  // cancel the temporary "stay on"s
   if (rotate_axle->compensating_lifter)
      motor_num_to_descr[rotate_axle->compensating_lifter]->temp_on = false;
   return NULL; }

void do_zero(const char** pptr) {  // zero {Fn|An|Sn|RR} [calibrate]
   struct motord_t* rotate_axle;
   struct fct_move_t* lift_move;
   int chr;
   lift_move = do_function(fct_zero, pptr);  // parse the wheel (F,A,S,RR) and get the finger lifter
   if (!lift_move) return;
   bool calibrate = scan_key(pptr, "calibrate"); // are we doing calibration?
   if (script_step && !do_step_wait()) return;
   rotate_axle = move_to_switch(lift_move);  // first move to the switch point
   if (!rotate_axle) return;
   // At this point rotate_axle->temp_on has been set (and also for the compensating lifter) to keep the
   // motors on during this process. Don't return without setting it off, or else they will never turn off.
   if (calibrate) { // create a new calibration value
      Serial.printf("hit space, 1-9, or a-z until wheel is at zero and aligned, then hit Enter; ESC aborts\n");
      // 'i' is 18 degrees, which is 1 digit position when there are two 0..9 repetitions around the digit wheel
      int degrees = 0, delta_degrees;
      while (1) {
         delta_degrees = 0;
         chr = wait_for_char();
         if (chr == ESC || chr == '\n') break;
         if (chr >= '1' && chr <= '9') delta_degrees = chr - '1';
         if (chr >= 'a' && chr <= 'z') delta_degrees = chr - 'a' + 10;
         if (chr == ' ') delta_degrees = 1;
         if (delta_degrees) { // move the wheel the number of degrees chosen
            queue_movement(rotate_axle, ROTATE, delta_degrees);
            if (!do_movements(timeunit_degree_usec)) goto cleanup;
            delay(DEBOUNCE); // let the switch settle
            degrees += delta_degrees; } }
      if (chr == '\n') { // we're done; update the configuration (else: abort)
         //if (degrees > 180)  // shorter by going counter-clockwise?
         //   degrees -= 360;  // NO! The finger must always move clockwise after the switch is triggered or else it's not on the nib
         int* target = &config.finger_zero_degrees[rotate_axle->motor_number].degrees;
         Serial.printf("axle %s zero changed from %d to %d degrees past the switch\n",
                       rotate_axle->axle_name, *target, degrees);
         *target = degrees;  //make the change
         write_config(); } }
   else { // zero using existing calibration
      int degrees = config.finger_zero_degrees[rotate_axle->motor_number].degrees;
      if (degrees == -1) error("axle not calibrated", rotate_axle->axle_name);
      else {
         if (debug >= 1) Serial.printf("rotating %s %d degrees to zero\n", rotate_axle->axle_name, degrees);
         queue_movement(rotate_axle, ROTATE, degrees);  // now make the final adjustment to zero
         do_movements(timeunit_degree_usec * degrees); } }
cleanup:
   rotate_axle->temp_on = false; // cancel the temporary "stay on"s
   if (rotate_axle->compensating_lifter)
      motor_num_to_descr[rotate_axle->compensating_lifter]->temp_on = true;
   return; }

void do_calibrate(const char **pptr) { // store a calibration value, as in "calibrate s1r 47"
   struct motord_t* pmd;
   if ((pmd = scan_axlename(pptr, ROTATE, true))) {
      int degrees;
      if (scan_int(pptr, &degrees, -360, +360)) {
         int* target = &config.finger_zero_degrees[pmd->motor_number].degrees;
         Serial.printf("axle %s zero changed from %d to %d degrees past the switch\n",
                       pmd->axle_name, *target, degrees);
         *target = degrees;  //make the change
         write_config(); }
      else error("bad degrees", *pptr); } }
//*
