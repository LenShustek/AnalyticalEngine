/***************************************************************************************************

   -----  Control program for the Analytical Engine prototype  -----

    The AE prototype is a testbed for some Babbage-designed 19th century mechanisms. 
    It is driven for testing from the level below by 21st century stepper motors and
    electronics. This is the control program for its Teensy microcomputer.
    
    The following axles are implemented in the first 4-digit prototype:

      F    the anticipating carriage digit wheels
      C    carry sectors for adding/subtracting 1 to F
      FC   the connector pinion between F and FP
      FP   the fixed long pinions
      FPC  the connector pinion between FP and either A1 or A2
      MP   the movable long pinions
      MPC  the connector pinion between MP and either A1 or A2
      A1   the upper number in the digit wheel stack
      A2   the lower number in the digit wheel stack

    The axles can be connected thusly:

     C  -- F -- FC -- FP == FPC -- \
                      ||            -- A1/A2
                      MP == MPC -- /

   Double lines represent axles that are always connected, but the
   FP==MP connection can be from MP to the FP above, which does a shift.
   Connecting both FPC and MPC to the same A digit wheel creates a jam.

   There are seven stepper motors that rotate and lift wheels and pinions.
   There are also three motors to control locks for F, A1, and A2, and
   two motors that position the fingers inside the digit wheels of F and A1/A2.
   All are controlled by the Teensy microcomputer as directed by a USB serial console.

   primitive movement commands
       rot <axlename> <signed degrees>   // rotate a shaft the specified degrees; positive is clockwise
       lift <axlename> <signed mils>     // lift (positive) or lower a shaft the specified thousandths of an inch

   functional movement commands
       {lock | unlock} {F | A1 | A2}     // control digit wheel locks
       mesh FC                           // create the F==FP link
       mesh {FPC | MPC} {A1 | A2}        // create the link from FP or MP to A1 or A2
       unmesh {FC | FPC | MPC}           // break the specific link
       finger {F | A1 | A2}              // make the giving-off finger engage with the named digit wheel
       nofinger {F | A}                  // make the giving-off finger not engaged
       zero {F | A1 | A2}                // reset the finger rotational position and zero the digit wheels
       calibrate {F | A}                 // calibrate the rotational position sensor (need only be done once for each axle)
       giveoff {F | A}                   // rotate the digit wheel finger down one digit
       setcarry {0 | 9 | reset}          // carry chain positioning: for 0's or 9's, or to reset the carry warning
       carry {up | down | add | sub}     // lift the carry warning levers, or rotate the carry sectors to add/sub 1
       keepers {up | down |              // lift or rotate the carry sector keepers
             none | top | both}

   multi-step movement commands
       run <script>            // run a predefined cycle of operations
       step <script>           // same, but wait for input between steps

   control commands
       off                     // turn off all motors so things can be moved by hand
       on                      // energize and lock all motors
       home                    // move everything to the initial positions
       reset                   // reset the internal state to initial positions without moving
       timeunit <msecs>        // set the time duration that basic operations take
       debug n                 // request debug output, from 0 (none) to 3 (lots)

   Except for the rotational position of the finger axles that can be initialized with
   the "zero" command, the machine cannot sense the current state. It assumes the
   following initial conditions on startup or after the "reset" command is issued:

      lock F; lock A1; lock A2
      unmesh FC; unmesh FPC; unmesh MPC
      nofinger F; nofinger A;
      setcarry 9; keepers top

   Information about the rotational position sensor that is gathered by the "calibrate"
   command is recorded in non-voltaile EEPROM memory and loaded on startup.

   Commands are entered from a serial console, which should be set for "newline" as the
   ending character. We use the Coolterm terminal emulator because the Arduino Serial Monitor
   doesn't allow reading individual characters until Enter has been hit.

   Several commands can be on one line, separated by semicolons.
   Hitting "Enter" on an empty line repeats the last command.
   Hitting "backspace" on an empty line repeats the next-to-last command.

   The NEMA 17 60mm stepper motor spec max is 3.36 VDC at 2.1A into 1.6 ohms. Set the
   reference voltage on the DRV8825 driver board to about 0.8V to limit the current 
   to 1.6A. To further limit torque on certain motors, lower the reference voltage.

   We use quarter-step micro-stepping, so the holding torque is reduced to about 38%
   compared to full stepping. But apparently pull-out torque is not; see these:
   See https://embeddedtronicsblog.wordpress.com/2020/09/03/torque-vs-microstepping/
   and https://www.rototron.info/wp-content/uploads/PiStepper_Microstepping_WP.pdf.

   ---- change log ----
   14 Mar 2024, L. Shustek, started, compatible with Teensy 3.5, 3.6, or 4.1.
   19 May 2024, L. Shustek, various changes and additions
   ******************************************************************************************************/

#define uSTEPS_PER_STEP 4            // how many microsteps per step the drivers are configured for (MODE1 high)
#define STEPS_PER_ROTATION 200       // 1.8 degree step angle for Nema 11 2-phase stepper motor
#define LIFT_MILS_PER_ROTATION 315   // lead screw lift is 8mm/rotation, or 314.96 mils 
#define NUM_MOTORS 24                // maximum possible motors; 16 are currently implemented)
#define DIGIT_REPETITIONS 3          // number of repetitions of 0-9 on each wheel
#define DEFAULT_TIMEUNIT_MSEC 500    // default time unit for moving one digit
#define DEBOUNCE  25                 // switch debounce time in msec

#define uSTEPS_PER_ROTATION (uSTEPS_PER_STEP * STEPS_PER_ROTATION)
#define DEGREES_PER_DIGIT (360/10/DIGIT_REPETITIONS)

// Teensy hardware

#include <EEPROM.h>
#define MOTOR_FAULT 2       // active low input: motor fault detected
#define MOTOR_ENB 3         // active low output: enable all motors
#define MOTOR_DIR 4         // direction control for all motors
#define A_ROTATE_INDEX 32   // low when A rotator hits the index point
#define F_ROTATE_INDEX 31   // low when F rotator hits the index point

// the 24 possible motors are in three groups of 8 per driver board
const byte motor_step_pins [] = { // map motor numbers 0..23 to STEP Teensy 3.5 pins
   9, 10, 11, 12, 8, 7, 6, 5,          // group 1 (left) 0...7
   17, 18, 19, 20, 16, 15, 14, 13,     // group 2 (middle) 8..15
   25, 26, 27, 28, 24, 23, 22, 21 };   // group 3 (right) 16..23

// symbolic names for motor numbers from 0..23 as positioned on the boards
// so that the cables from the motors reach the boards with minimum tangles;
// see the Excel spreadsheet for a physical map
#define F_L    11  // carriage wheel finger lift
#define F_R    10  // carriage wheel finger rotate
#define A_L    18  // input figure wheel finger lift
#define A_R    21  // input figure wheel finger rotate
#define FC_L   23  // carriage wheel connector lift
#define MP_L   16  // movable long pinion lift
#define MPC_L  22  // movable long pinion connector lift
#define FPC_L  17  // fixed long pinion connector lift
#define W_R     9  // carriage fixed wire rotate
#define N_L    14  // carry warning arms lift
#define C_R    13  // carry sector rotate
#define H_R     8  // carry sector keepers rotate
#define H_L    15  // carry sector keepers lift
#define FK_R   12  // carriage wheel lock rotate
#define A1K_R  20  // input figure wheel top digit lock rotate
#define A2K_R  19  // input figure wheel bottom digit lock rotate
// 8 more numbered from 0 to 7 can be added...

enum movement_t {ROTATE, LIFT };  // movement types

struct motord_t { //**** a motor descriptor
   int motor_number;                    // 0..23, as defined symbolically above
   enum movement_t motor_type;          // does it rotate or lift?
   const char *axle_name;               // name used in the "rot" or "lift" commands
   unsigned gear_ratio;                 // if not zero, gear reduction ratio x 1000
   int finger_zero_degrees;             // for A and F: zero is this number of degrees past the switch point
   bool moving;                         // is this motor scheduled for movement?   
   bool clockwise;                      // in which direction?
   unsigned usteps_needed, usteps_done; // how many movement pulses are needed, and done
   unsigned long last_ustep_time_usec;  // when the last step was done
   int current_position;                // current position relative to neutral, in units that depend on the axle
}
motor_descriptors[] = {  // an unordered list of descriptors for motors
   //  put longer names first so they get scanned first in case later ones are prefixes
   {A1K_R, ROTATE, "a1k" },
   {A2K_R, ROTATE, "a2k" },
   {MPC_L, LIFT, "mpc" },
   {FPC_L, LIFT, "fpc" },
   {FK_R, ROTATE, "fk" },
   {FC_L, LIFT, "fc" },
   {MP_L, LIFT, "mp" },
   {A_L, LIFT, "al" },
   {A_R, ROTATE, "ar", 4154, -10 }, // has 54/13 = 4.15385 gearset
   {F_L, LIFT, "fl" },
   {F_R, ROTATE, "fr", 4154, -10 }, // has 54/13 = 4.15385 gearset
   {C_R, ROTATE, "c" },
   {W_R, ROTATE, "w" },
   {N_L, LIFT, "n" },
   {H_R, ROTATE, "h" },
   {H_L, LIFT, "h" },
   { -1 } };

struct motord_t *motor_num_to_descr [NUM_MOTORS] // map from motor number to motor descriptor
      = {0 };

//***** functional motor movements

struct fct_move_t { // basic movement specification
   const char *keyword1;  // primary keyword identifying axle to move
   const char *keyword2;  // optional secondary keyword
   int motor_num;         // the axle to move
   int position; }        // where it should move to

fct_unlock[] = {
   {"F", NULL, FK_R, 30 },
   {"A1", NULL, A1K_R, 24 },
   {"A2", NULL, A2K_R, -24 }, { } },
fct_lock[] = {
   {"F", NULL, FK_R, 0 },
   {"A1", NULL, A1K_R, 0 },
   {"A2", NULL, A2K_R, 0 }, { } },
fct_mesh[] = {
   {"FC", NULL, FC_L, 375 },
   {"FPC", "A1", FPC_L, 375 },
   {"FPC", "A2", FPC_L, -375 },
   {"MPC", "A1", MPC_L, 375 },
   {"MPC", "A2", MPC_L, -375 }, { } },
fct_unmesh[] = {
   {"FC", NULL, FC_L, 0 },
   {"FPC", NULL, FPC_L, 0 },
   {"MPC", NULL, MPC_L, 0 }, { } },
fct_finger[] = {
   {"F", NULL, F_L, -225 },
   {"A1", NULL, A_L, 275 },  // extra 75 mils for backlash
   {"A2", NULL, A_L, -275 }, { } },
fct_calibrate[] = { // same values as for fct_finger
   {"F", NULL, F_L, -225 },
   {"A", NULL, A_L, 275 }, { } }, // use A1 for calibration
fct_nofinger[] = {
   {"F", NULL, F_L, 0 },
   {"A", NULL, A_L, 0 }, { } },
fct_setcarry[] = {
   {"9", NULL, W_R, 0 },
   {"0", NULL, W_R, -28 },
   {"RESET", NULL, W_R, 33 }, { } },
fct_carry[] = {
   {"up", NULL, N_L, 400 },
   {"down", NULL, N_L, 0 },
   {"add", NULL, W_R, 12 },
   {"sub", NULL, W_R, -12 }, { } },
fct_keepers[] = {
   {"none", NULL, H_R, 0 },
   {"top", NULL, H_R, 45 },
   {"both", NULL, H_R, 90 },
   {"up", NULL, H_L, 250 },
   {"down", NULL, H_L, 0 }, { } };

// predefined scripts

struct script_t {
   const char *name;         // the name of the script
   const char **commands; }  // pointer to an array of commands

home_commands = {"home", (const char *[]) { // reset everything to initial positions
   // all of it is done in one time unit
   "lock F; lock A1; lock A2; unmesh FC; unmesh FPC; unmesh MPC; "
   "nofinger F; nofinger A; setcarry 9; keepers top",
   NULL } },

named_scripts[] = { // scripts that are searched by name for "run" and "step"
   {
      "zero", (const char *[]) { // zero the number on A1
         "finger A1; unlock A1",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "nofinger A; lock A1",
         "giveoff A",
         NULL  } },
   {
      "copy", (const char *[]) { // transfer the number on A1 to F
         "finger A1; mesh FC; mesh MPC A1; unlock F; unlock A1",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "nofinger A; unmesh FC; unmesh MPC; lock F; lock A1",
         "giveoff A",
         NULL  } },
   {
      "add", (const char *[]) { // add the number on A1 to F
         "finger A1; mesh FC; mesh MPC A1; keepers none; unlock F; unlock A1",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "giveoff A",
         "nofinger A; unmesh FC; unmesh MPC; carry up; keepers up; lock F; lock A1",
         "giveoff A; keepers both",
         "carry down; unlock F",
         "carry add",
         "setcarry reset; keepers top; lock F",
         "setcarry 9; keepers down",
         NULL } },
   // add more scripts here...
   {
      NULL } };

struct { // the configuration record written to non-volatile EEPROM memory
#define CONFIG_ID "Babbage"
   char id[8];
   int a_finger_zero_degrees;
   int f_finger_zero_degrees; } config = {0 };

//****  initialization

unsigned long timeunit_usec = DEFAULT_TIMEUNIT_MSEC * 1000L; // to move one digit, or lift, or lock, etc.
                                                    // the AE Plan 16 through Plan 28 target is 157 msec

// the time to move one degree is computed to have the same circumferential speed as moving one digit
#define timeunit_degree_usec (timeunit_usec * 10 * DIGIT_REPETITIONS / 360)

int debug = 1;               // debug level from 0 to 3
int motors_moving = 0;       // how many motors are currently queued up to move
bool got_error = false;      // was an error generated during this action?

void read_config(void) {
   for (unsigned i = 0; i < sizeof(config); ++i)
      ((char *)&config)[i] = EEPROM.read(i);
   if (strncmp(config.id, CONFIG_ID, sizeof(config.id)) != 0)
      Serial.printf("*** no config block in EEPROM\n");
   else {
      motor_num_to_descr[A_R]->finger_zero_degrees = config.a_finger_zero_degrees;
      motor_num_to_descr[F_R]->finger_zero_degrees = config.f_finger_zero_degrees;
      Serial.printf("A finger adjustment is %d degrees, F finger adjustment is %d degrees\n",
                    config.a_finger_zero_degrees, config.f_finger_zero_degrees); } }

void write_config(void) {
   strcpy(config.id, CONFIG_ID);
   for (unsigned i = 0; i < sizeof(config); ++i)
      EEPROM.write(i, ((char *)&config)[i]);
   Serial.printf("config block written\n"); }

void setup(void) {
   pinMode(MOTOR_FAULT, INPUT_PULLUP);
   pinMode(MOTOR_DIR, OUTPUT);
   digitalWrite(MOTOR_ENB, HIGH); pinMode(MOTOR_ENB, OUTPUT); digitalWrite(MOTOR_ENB, HIGH);
   for (unsigned i = 0; i < NUM_MOTORS; ++i) {
      pinMode(motor_step_pins[i], OUTPUT); }  // pulse 2 usec high to step
   pinMode(A_ROTATE_INDEX, INPUT_PULLUP);
   pinMode(F_ROTATE_INDEX, INPUT_PULLUP);

   Serial.begin(115200);
   delay(500);
   while (!Serial.available()) ; // wait for terminal emulator to connect and user to hit Enter
   Serial.printf("*** AE prototype tester ***\ntimeunit is %d msec\n", timeunit_usec / 1000L);

   // create a map from motor number to motor descriptor
   for (struct motord_t *pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      int motornum = pmd->motor_number;
      if (motor_num_to_descr[motornum]) Serial.printf("ERROR: motor %u is duplicated!\n", motornum);
      motor_num_to_descr[motornum] = pmd; }

   static const char *intro[] = {
      "We assume the following neutral positions:\n",
      " - all 3 digit wheels locked\n",
      " - all 8 lifts at their red marks\n",
      " - the top sector keepers are above the carry sectors, but not below\n",
      " - all carry warning arms in the unwarned position\n",
      " - the wire carrier reset pins are just clear of the carriage wheels\n",
      NULL };
   for (const char **msg = intro; *msg; ++msg)
      Serial.print(*msg);
   motor_num_to_descr[H_R]->current_position = 45;
   read_config(); }

//****  command parsing routines

void scan_commands(const char *cmds) ;
#define CMDLENGTH 150
static char prev_cmd[CMDLENGTH] = {0}, prev_prev_cmd[CMDLENGTH] = {0};

void error(const char *msg, const char *info) {
   Serial.printf("%s%c %s\n", msg, *info ? ':' : ' ', info);
   got_error = true; }

void flush_input(void) {
   //Serial.flush() flushes the *output* channel!
   while (Serial.available()) Serial.read(); }

void getstring(char *buf, unsigned buflen) { // get a command string from the keyboard
   unsigned ndx;
   flush_input();
   Serial.print('>');
   for (ndx = 0; ndx < buflen - 1; ++ndx) {
      while (Serial.available() == 0) ; // wait for a character
      char ch = Serial.read();
      if (ch == '\n') break;
      if (ch == '\b') { // backspace
         if (ndx > 0) ndx -= 2;  // remove a typed character
         else { // backspace when empty: do previous previous command
            strncpy(buf, prev_prev_cmd, buflen);
            strncpy(prev_cmd, prev_prev_cmd, sizeof(prev_cmd));
            return; } }
      else  buf[ndx] = ch; }
   if (ndx == 0) { // empty return: repeat last command
      strncpy(buf, prev_cmd, buflen); }
   else {
      buf[ndx] = 0;
      strncpy(prev_prev_cmd, prev_cmd, sizeof(prev_prev_cmd)); // save prev prev command
      strncpy(prev_cmd, buf, sizeof(prev_cmd)); } // save new one as prev command
   //Serial.printf(">%s\n", buf);
}

int wait_for_char(void) {
   flush_input();
   while (Serial.available() == 0) ;
   return Serial.read(); }

bool check_abort(void) { // check for conditions that abort the current movements
   if (Serial.available()) { // (1) any character from the keyboard
      Serial.println("aborted...");
      char chr = Serial.read();
      if (chr != '\e') // if it's not ESC ("stop NOW!")
         do_script(home_commands.commands, false); // return everything to home position
      return true; }
   if (digitalRead(MOTOR_FAULT) == LOW) { // (2) a motor fault
      error("motor fault", "");
      return true; }
   return false; }

void skip_blanks(const char **pptr) {
   while (**pptr == ' ' || **pptr == '\t' || **pptr == '\n' || **pptr == '\r') ++*pptr; }

bool scan_key(const char **pptr, const char *keyword) {
   skip_blanks(pptr);
   const char *temp_ptr = *pptr;
   do if (tolower(*temp_ptr++) != tolower(*keyword++)) return false;
   while (*keyword);
   *pptr = temp_ptr;
   skip_blanks(pptr);
   return true; }

bool scan_int(const char **pptr, int *pnum, int min, int max) {
   int num;  int nch;
   if (sscanf(*pptr, "%d%n", &num, &nch) != 1
         || num < min || num > max ) return false;
   *pnum = num;
   *pptr += nch;
   skip_blanks(pptr);
   return true; }

bool strmatch(const char *a, const char *b) {
   while (*a && *b)
      if (*a++ != *b++) return false;
   return *a == 0 && *b == 0; }

// Scan for an axle name of a particular movement type: LIFT or ROTATE.
// Return the pointer to the motor descriptor, or NULL if not found
struct motord_t *scan_axlename(const char **pptr, enum movement_t which) {
   const char *savep = *pptr;
   for (struct motord_t *pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      if (scan_key(pptr, pmd->axle_name) && pmd->motor_type == which) {
         return pmd; }
      *pptr = savep; }
   error("bad motor name", *pptr);
   return NULL; }

//****  movement queuing and execution

bool do_movements(unsigned long duration_usec) { // do all the movements queued up for this time unit
   // return true if everything worked ok
   if (motors_moving == 0) return true;
#define TICK_USEC 100  // how often to check for something to do
   digitalWrite(MOTOR_ENB, LOW); // enable the motors...when to disable, if ever?
   if (debug >= 2) Serial.printf("  doing movements for %d motors\n", motors_moving);
   int totalsteps = 0;
   while (motors_moving > 0) {  // while there are pending movements
      if (check_abort()) {
         motors_moving = 0;
         return false; }
      unsigned long timenow = micros();
      for (struct motord_t *pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
         if (pmd->moving) { // look at all the motors that are moving
            // do all required movements evenly spaced within one time unit
            if (timenow - pmd->last_ustep_time_usec >= duration_usec / pmd->usteps_needed) {
               digitalWrite(MOTOR_DIR, pmd->clockwise);
               int pin = motor_step_pins[pmd->motor_number];
               digitalWrite(pin, HIGH); // do one microstep
               delayMicroseconds(3); // TI DRV8825 stepper motor controller spec: pulse min 1.9 usec high
               digitalWrite(pin, LOW);
               ++totalsteps;
               pmd->last_ustep_time_usec = timenow;
               if (++pmd->usteps_done >= pmd->usteps_needed) { // if this motor is done
                  pmd->moving = false;
                  --motors_moving; } } } }
      delayMicroseconds(TICK_USEC); }
   if (debug >= 2) Serial.printf("     did %d steps\n", totalsteps);
   return true; }

void queue_movement ( // queue an elemental movement to happen during this time unit
   struct motord_t *pmd, int distance) {
   if (pmd == NULL) {
      Serial.printf("bad call to queue_movement!\n");
      return; }
   if (pmd->moving) {
      Serial.printf("axle %s is already scheduled to move\n", pmd->axle_name);
      return; }
   pmd->moving = true;
   ++motors_moving;
   if (pmd->motor_type == ROTATE) { // distance is signed degrees
      unsigned long gear_ratio = pmd->gear_ratio ? pmd->gear_ratio : 1000;
      pmd->usteps_needed = (abs(distance) * gear_ratio * uSTEPS_PER_ROTATION) / (360 * 1000);
      pmd->clockwise = distance > 0;
      if (debug >= 3) Serial.printf("  queued motor %s rotator %s %d degrees by %d microsteps\n",
                                       pmd->axle_name, pmd->clockwise ? "CW" : "CCW", abs(distance), pmd->usteps_needed); }
   else { // LIFT; distance is signed mils
      pmd->usteps_needed = (abs(distance) * uSTEPS_PER_ROTATION) / LIFT_MILS_PER_ROTATION;
      pmd->clockwise = distance > 0;
      if (debug >= 3) Serial.printf("  queued motor %s lifter %s %d mils by %d microsteps\n",
                                       pmd->axle_name, pmd->clockwise ? "CW" : "CCW", abs(distance), pmd->usteps_needed); }
   pmd->usteps_done = 0;
   pmd->last_ustep_time_usec = 0; }

void do_script(const char **commands, bool pause) { // run a sequence of commands
   int cyclenum = 0;
   while (1) { // for each time unit
      if (debug >= 1) Serial.printf("*** time unit %d: %s\n", ++cyclenum, *commands);
      scan_commands(*commands);
      if (got_error) break;
      if (!do_movements(timeunit_usec)) break;
      if (!*++commands) break;
      if (pause) {
         Serial.println("waiting...");
         while (1) {
            int key = wait_for_char();
            if (key == '\n') break;
            if (key == '\e') { // ESC
               Serial.println("aborted...");
               return; } } } }
   if (debug >= 1) Serial.println ("end of script"); }

void do_reset(void) { // reset our internal state, but not the hardware
   for (struct motord_t *pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      pmd->moving = false;
      pmd->current_position = 0; } }

void do_test(void) { // various changeable test code...
   Serial.println("do test");
   while (1) {
      int num;
      if ((num = Serial.available())) {
         Serial.printf("%d chars: ", num);
         while (Serial.available()) {
            char chr = Serial.read();
            if (chr == '\e') goto end;
            Serial.printf(" %02X", chr); }
         Serial.println(); } }
end:
   Serial.println("end test"); }

void show_indices(void) { // routine to check digit wheel index hardware
   int fi = -1, ai = -1;
   while (!Serial.available()) {
      if (digitalRead(F_ROTATE_INDEX) != fi) {
         delay(DEBOUNCE);
         fi = digitalRead(F_ROTATE_INDEX);
         Serial.printf("F index = %d\n", fi); }
      if (digitalRead(A_ROTATE_INDEX) != ai) {
         delay(DEBOUNCE);
         ai = digitalRead(A_ROTATE_INDEX);
         Serial.printf("A index = %d\n", ai); } }
   Serial.println("done"); }

//***** functional motor movement routines

void do_move(struct fct_move_t *move) { // queue up an elementary motion
   struct motord_t *pmd;
   pmd = motor_num_to_descr[move->motor_num];
   int desired_position = move->position;
   int distance = desired_position - pmd->current_position;
   if (distance == 0)
      Serial.printf("already there: %s\n", pmd->axle_name);
   else {
      queue_movement(pmd, distance);
      pmd->current_position = desired_position; } }

struct fct_move_t *do_function( // parse axle name(s) and queue up a move
   struct fct_move_t *move, const char **pptr) {
   const char *savep = *pptr;
   for (; move->keyword1; ++move) {
      if (scan_key(pptr, move->keyword1)) {
         if (move->keyword2) { // if there needs to be a second keyword
            if (!scan_key(pptr, move->keyword2)) { // check if it matches
               *pptr = savep; // if not, abort this match
               continue; } }
         do_move(move);
         return move; } }
   error("unknown axle", *pptr);
   return NULL; }

bool locked (int motor_num) {
   struct motord_t *md = motor_num_to_descr[motor_num];
   if (md->current_position == 0) {
      Serial.printf("ERROR: %s is locked!\n",  md->axle_name);
      return true; }
   return false; }

struct motord_t *move_to_switch(struct fct_move_t /*lifter*/ *move) {
   // Unlock and engage the digit wheel whose specified finger lift is queued up,
   // then go to the switch point. Return the axle being rotated.
   struct motord_t *rotate_axle;
   int switch_port;
   switch (move->motor_num) {
      case F_L:
         rotate_axle = motor_num_to_descr[F_R];
         switch_port = F_ROTATE_INDEX;
         scan_commands("mesh FC");  // engage the long pinions to provide some drag?
         scan_commands("unlock F");
         break;
      case A_L:
         rotate_axle = motor_num_to_descr[A_R];
         switch_port = A_ROTATE_INDEX;
         scan_commands(move->position > 0 ? "unlock A1" : "unlock A2");
         break;
      default:
         error("bad move_to_switch finger axle", "");
         return NULL; }
   if (!do_movements(timeunit_usec)) // lift to engage the finger and unlock
      return NULL;
   if (debug >= 1) Serial.printf("rotating %s 10 digits\n", rotate_axle->axle_name);
   queue_movement(rotate_axle, DEGREES_PER_DIGIT * 10); // rotate 10 digits to ensure the wheel engages with the finger
   if (!do_movements(timeunit_usec * 10)) return NULL;
   int limit = 370;
   while (--limit && digitalRead(switch_port) == 0) { // if it's sitting on the switch
      if (debug >= 1) Serial.printf("getting %s off the switch\n", rotate_axle->axle_name);
      queue_movement(rotate_axle, 1 /*degree*/); // get it off
      if (!do_movements(timeunit_degree_usec)) return NULL; }
   if (!limit) error("switch is always on!", "");
   else {
      limit = 370;
      if (debug >= 1) Serial.printf("rotating %s to the switch position\n", rotate_axle->axle_name);
      while (--limit && digitalRead(switch_port) == 1) { // now rotate until it just gets on the switch
         // don't need to find the center point, since we always approach it the same way
         queue_movement(rotate_axle, 1 /*degree*/);
         if (!do_movements(timeunit_degree_usec)) return NULL; }
      if (!limit) {
         error ("switch is always off!", "");
         return NULL; } }
   return rotate_axle; }

void do_zero_reset (    // cleanup after "calibrate" or "zero" commands
   struct motord_t *rotate_axle, struct fct_move_t *lift_move) {
   if (rotate_axle->motor_number == F_R) {
      scan_commands("unmesh FC"); // unmesh the long pinions to remove drag
      scan_commands("nofinger F; lock F"); } // disengage the finger and lock
   else { // A_R
      scan_commands("nofinger A"); // disengage the finger
      scan_commands(lift_move->position > 0 ? "lock A1" : "lock A2"); }
   if (do_movements(timeunit_usec)) { // do finger disengagement and locking
      if (debug >= 1) Serial.printf("rotating %s past the nib\n", rotate_axle->axle_name);
      queue_movement(rotate_axle, DEGREES_PER_DIGIT); // rotate one digit past the nib
      do_movements(timeunit_usec); } }

void do_zero(const char **pptr) { // zero F or A1 or A2
   struct motord_t *rotate_axle;
   struct fct_move_t *lift_move;
   lift_move = do_function(fct_finger, pptr); // parse the wheel (F, A1, or A2), get the finger lifter, and queue finger lift
   if (lift_move) {
      rotate_axle = move_to_switch(lift_move); // engage the digit wheel and move to the switch point
      if (rotate_axle) {
         if (debug >= 1) Serial.printf("rotating %s %d degrees to zero\n",
                                          rotate_axle->axle_name, rotate_axle->finger_zero_degrees);
         queue_movement(rotate_axle, rotate_axle->finger_zero_degrees); // now make the final adjustment to zero
         if (do_movements(timeunit_degree_usec * rotate_axle->finger_zero_degrees))
            do_zero_reset(rotate_axle, lift_move); } } }

void do_calibrate(const char **pptr) { // record how many degrees past the switch point is zero
   struct motord_t *rotate_axle;
   struct fct_move_t *lift_move;
   lift_move = do_function(fct_calibrate, pptr); // parse the axle (F or A), get the finger lifter, and queue finger lift
   if (lift_move) {
      rotate_axle = move_to_switch(lift_move); // engage the digit wheel and move to the switch point
      if (rotate_axle) {
         Serial.printf("hit space until digit wheel is at zero, then hit Enter; ESC aborts\n");
         rotate_axle->finger_zero_degrees = 0;
         while (1) {
            int chr = wait_for_char();
            if (chr == '\e') {
               Serial.println("*** aborted");
               return; }
            if (chr == '\n') break;
            if (chr == ' ') {
               queue_movement(rotate_axle, 1/*degree*/); // rotate one degree
               if (!do_movements(timeunit_degree_usec)) return;
               delay(DEBOUNCE);
               ++rotate_axle->finger_zero_degrees; } }
         if (rotate_axle->finger_zero_degrees > 180) // shorter by going counter-clockwise?
            rotate_axle->finger_zero_degrees -= 360;
         Serial.printf("axle %s zero is %d degrees past the switch\n",
                       rotate_axle->axle_name, rotate_axle->finger_zero_degrees);
         if (rotate_axle->motor_number == F_R)
            config.f_finger_zero_degrees = rotate_axle->finger_zero_degrees;
         else config.a_finger_zero_degrees = rotate_axle->finger_zero_degrees;
         write_config();
         do_zero_reset(rotate_axle, lift_move); } } }

void do_giveoff(const char **pptr) { // give off one digit
   struct motord_t *axle, *finger;
   if (scan_key(pptr, "F")) {
      if (locked(FK_R)) return;
      axle = motor_num_to_descr[F_R];
      finger = motor_num_to_descr[F_L];
      goto domove; }
   else if (scan_key(pptr, "A")) {
      axle = motor_num_to_descr[A_R];
      finger = motor_num_to_descr[A_L]; }
   else {
      error("bad axle", *pptr);
      return; }
   if ((finger->current_position > 0 && locked(A1K_R))
         || (finger->current_position < 0 && locked(A2K_R)))  return;
domove:
   if (finger->current_position == 0) Serial.printf("** warning: finger for %s not engaged\n", finger->axle_name);
   queue_movement(axle, DEGREES_PER_DIGIT); }

//***** command interpreter

struct script_t * find_script(const char **pptr) {
   for (struct script_t *sp = named_scripts; sp->name; ++sp)
      if (scan_key(pptr, sp->name)) return sp;
   error("unknown script name", *pptr);
   return NULL; }

void scan_commands(const char *ptr) {  // can be called recursively!
   struct script_t *sp;
   got_error = false;
   skip_blanks(&ptr);
   //if (debug >= 1) Serial.printf(":%s\n", ptr);
   while (!got_error && *ptr) { // do all the commands on one line
      if (scan_key(&ptr, "rot ")) {
         struct motord_t *pmd;
         int degrees;
         if ((pmd = scan_axlename(&ptr, ROTATE))) {
            if (scan_int(&ptr, &degrees, -360, +360))
               queue_movement(pmd, degrees);
            else error ("bad degrees", ptr); } }
      else if (scan_key(&ptr, "lift" )) {
         struct motord_t *pmd;
         int mils;
         if ((pmd = scan_axlename(&ptr, LIFT))) {
            if (scan_int(&ptr, &mils, -750, +750))
               queue_movement(pmd, mils);
            else error("bad mils", ptr); } }
      else if (scan_key(&ptr, "lock")) do_function(fct_lock, &ptr);
      else if (scan_key(&ptr, "unlock")) do_function(fct_unlock, &ptr);
      else if (scan_key(&ptr, "mesh")) do_function(fct_mesh, &ptr);
      else if (scan_key(&ptr, "unmesh")) do_function(fct_unmesh, &ptr);
      else if (scan_key(&ptr, "finger")) do_function(fct_finger, &ptr);
      else if (scan_key(&ptr, "nofinger")) do_function(fct_nofinger, &ptr);
      else if (scan_key(&ptr, "zero")) do_zero(&ptr);
      else if (scan_key(&ptr, "calibrate")) do_calibrate(&ptr);
      else if (scan_key(&ptr, "giveoff")) do_giveoff(&ptr);
      else if (scan_key(&ptr, "setcarry")) do_function(fct_setcarry, &ptr);
      else if (scan_key(&ptr, "carry")) do_function(fct_carry, &ptr);
      else if (scan_key(&ptr, "keepers")) do_function(fct_keepers, &ptr);
      else if (scan_key(&ptr, "timeunit ")) {
         int timeunit_msec;
         if (scan_int(&ptr, &timeunit_msec, 10, 5000))
            timeunit_usec = timeunit_msec * 1000L;
         else error("bad time in msec", ptr); }
      else if (scan_key(&ptr, "debug ")) {
         if (!scan_int(&ptr, &debug, 0, 5)) error("bad debug level", ptr); }
      else if (scan_key(&ptr, "run")) {
         if ((sp = find_script(&ptr))) do_script(sp->commands, false); }
      else if (scan_key(&ptr, "step")) {
         if ((sp = find_script(&ptr))) do_script(sp->commands, true); }
      else if (scan_key(&ptr, "on")) digitalWrite(MOTOR_ENB, LOW);
      else if (scan_key(&ptr, "off")) digitalWrite(MOTOR_ENB, HIGH);
      else if (scan_key(&ptr, "home")) do_script(home_commands.commands, false);
      else if (scan_key(&ptr, "reset")) do_reset();
      else if (scan_key(&ptr, "test")) do_test();
      else if (scan_key(&ptr, "indices")) show_indices();
      else error ("bad command", ptr);
      scan_key(&ptr, ";"); } }

//****  the main loop

void loop(void) {
   char cmdline[CMDLENGTH];
   getstring(cmdline, sizeof(cmdline)); // get and parse commands
   scan_commands(cmdline);
   do_movements(timeunit_usec); // do any queued "rot" and "lift" movements
}

//*
