#include "prototype.h"

//***** functional motor movements

struct fct_move_t
   fct_giveoff[] = {
   {"A2", A2_R }, {"A2", A2_R }, {"A2", A2_R },
   {"F2", F2_R }, {"F3", F3_R },
   {"S1", S1_R }, {"S2", S2_R }, {"S3", S3_R }, {"S4", S4_R }, {"S5", S5_R }, {"S6", S6_R },
   {"RR", RR_R }, { } },
fct_lock[] = {
   { "A1 top", A1K_L, -300 }, { "A1 bot", A1K_L, +300 }, {"A1", A1K_L, 0 },
   { "A2 top", A2K_L, -300 }, { "A2 bot", A2K_L, +300 }, {"A2", A2K_L, 0 },
   { "A3 top", A3K_L, -300 }, { "A3 bot", A3K_L, +300 }, {"A3", A1K_L, 0 },
   { "FP1", FP1K_R, 0 }, {"MP1", MP1K_R, 0 },
   { "FP2", FP2K_R, 0 }, {"MP2", MP2K_R, 0 },
   { "FP3", FP3K_R, 0 }, {"MP3", MP3K_R, 0 }, { } },
fct_lock1[] = {
   {"FP1", FP1K_R, 30 }, {"MP1", MP1K_R, 30 },
   {"FP2", FP2K_R, 30 }, {"MP2", MP2K_R, 30 },
   {"FP3", FP3K_R, 30 }, {"MP3", MP3K_R, 30 }, { } },
fct_unlock[] = {
   { "A1 top", A1K_L, +300 }, { "A1 bot", A1K_L, -300 }, {"A1", A1K_L, +550 },
   { "A2 top", A2K_L, +300 }, { "A2 bot", A2K_L, -300 }, {"A2", A2K_L, +550 },
   { "A3 top", A3K_L, +300 }, { "A3 bot", A3K_L, -300 }, {"A3", A1K_L, +550 },
   { "FP1", FP1K_R, 15 }, {"MP1", MP1K_R, 15 },
   { "FP2", FP2K_R, 15 }, {"MP2", MP2K_R, 15 },
   { "FP3", FP3K_R, 15 }, {"MP3", MP3K_R, 15 }, { } },
fct_mesh[] = {
   {"FP1 A1 top", P12_L, 400 }, {"FP1 A1 bot", P12_L, -400 }, {"MP1 A1 top", P11_L, 400 }, {"MP1 A1 bot", P11_L, -400 },
   {"FP1 A2 top", P14_L, 400 }, {"FP1 A2 bot", P14_L, -400 }, {"MP1 A2 top", P13_L, 400 }, {"MP1 A2 bot", P13_L, -400 },
   {"FP2 A2 top", P22_L, 400 }, {"FP2 A2 bot", P22_L, -400 }, {"MP2 A2 top", P21_L, 400 }, {"MP2 A2 bot", P21_L, -400 },
   {"FP2 A3 top", P24_L, 400 }, {"FP2 A3 bot", P24_L, -400 }, {"MP2 A3 top", P23_L, 400 }, {"MP2 A3 bot", P23_L, -400 },
   {"FP3 A3 top", P32_L, 400 }, {"FP3 A3 bot", P32_L, -400 }, {"MP3 A3 top", P31_L, 400 }, {"MP3 A3 bot", P31_L, -400 },
   {"RP1 A1 top", RP1_L, 1220 }, {"RP1 A1 bot", RP1_L, 370 }, {"RP1 MP1", RP1_L, (1220 + 370) / 2 },
   {"RP2 A2 top", RP2_L, 1220 }, {"RP2 A2 bot", RP2_L, 370 }, {"RP2 MP2", RP2_L, (1220 + 370) / 2 },
   {"REV2", REV2_L, 400 },  { "FC2", FC2_L, 400 },
   {"REV3", REV3_L, 400 },  { "FC3", FC3_L, 400 },
#define STORE_RACK 270     // how far in mils to move the store digit wheels to engage with only the rack, for writing
#define STORE_FINGER 525   // how far to move to engage with both the rack and the finger, for reading
   {"S1 top rack", S1_L, -STORE_RACK }, {"S1 bot rack", S1_L, STORE_RACK }, {"S1 top finger", S1_L, -STORE_FINGER }, {"S1 bot finger", S1_L, STORE_FINGER},
   {"S2 top rack", S2_L, -STORE_RACK }, {"S2 bot rack", S2_L, STORE_RACK }, {"S2 top finger", S2_L, -STORE_FINGER }, {"S2 bot finger", S2_L, STORE_FINGER },
   {"S3 top rack", S3_L, -STORE_RACK }, {"S3 bot rack", S3_L, STORE_RACK }, {"S3 top finger", S3_L, -STORE_FINGER }, {"S3 bot finger", S3_L, STORE_FINGER },
   {"S4 top rack", S4_L, -STORE_RACK }, {"S4 bot rack", S4_L, STORE_RACK }, {"S4 top finger", S4_L, -STORE_FINGER }, {"S4 bot finger", S4_L, STORE_FINGER },
   {"S5 top rack", S5_L, -STORE_RACK }, {"S5 bot rack", S5_L, STORE_RACK }, {"S5 top finger", S5_L, -STORE_FINGER }, {"S5 bot finger", S5_L, STORE_FINGER },
   {"S6 top rack", S6_L, -STORE_RACK }, {"S6 bot rack", S6_L, STORE_RACK }, {"S6 top finger", S6_L, -STORE_FINGER }, {"S6 bot finger", S6_L, STORE_FINGER },
   {"RR top rack", RR_L, -STORE_RACK }, {"RR bot rack", RR_L, STORE_RACK }, {"RR top finger", RR_L, -STORE_FINGER }, {"RR bot finger", RR_L, STORE_FINGER },
   { } },
fct_unmesh[] = {
   {"FP1 A1", P12_L, 0 }, {"MP1 A1", P11_L, 0 }, {"FP1 A2", P14_L, 0 }, {"MP1 A2", P13_L, 0 },
   {"FP2 A2", P22_L, 0 }, {"MP2 A2", P21_L, 0 }, {"FP2 A3", P24_L, 0 }, {"MP2 A3", P23_L, 0 },
   {"FP3 A3", P32_L, 0 }, {"MP3 A3", P31_L, 0 },
   {"S1", S1_L, 0 },  {"S2", S2_L, 0 },  {"S3", S3_L, 0 },  {"S4", S4_L, 0 },  {"S5", S5_L, 0 },  {"S6", S6_L, 0 }, {"RR", RR_L, 0 },
   {"RP1", RP1_L, 0 }, {"RP2", RP2_L, 0 }, {"RP3", RP3_L, 0 },
   {"REV2", REV2_L, 0 }, {"FC2", FC2_L, 0 },
   {"REV3", REV3_L, 0 }, {"FC3", FC3_L, 0 }, { } },
fct_finger[] = { { "F2", F2_L, -275 }, {"F3", F3_L, -275 },
   {"A1 top", A1_L, 275 }, { "A1 bot", A1_L, -275 },
   {"A2 top", A2_L, 275 }, { "A2 bot", A2_L, -275 },
   {"A3 top", A3_L, 275 }, { "A3 bot", A3_L, -275 }, { } },
fct_nofinger[] = {
   {"F2", F2_L, 0 },  { "F3", F3_L, 0 },
   {"A1", A1_L, 0 }, {"A2", A2_L, 0 }, {"A3", A3_L, 0 },
   {"RR", RR_L, 0 }, { } },
fct_shift[] = { {"MP1 up", MP1_L, 500 }, { "MP1 down", MP1_L, 0 },
   {"MP2 up", MP2_L, 500 }, { "MP2 down", MP2_L, 0 },
   {"MP3 up", MP1_L, 500 }, { "MP3 down", MP3_L, 0 }, { } },
fct_zero[] = {
   // used for searching, but not moving
   {"F2", F2_L, NOMOVE }, {"F3", F3_L, NOMOVE },
   {"A1", A1_L, NOMOVE }, {"A2", A2_L, NOMOVE }, {"A3", A3_L, NOMOVE },
   {"S1", S1_L, NOMOVE }, {"S2", S2_L, NOMOVE }, {"S3", S3_L, NOMOVE }, {"S4", S4_L, NOMOVE }, {"S5", S5_L, NOMOVE }, {"S6", S6_L, NOMOVE },
   {"RR", RR_L, NOMOVE }, { } },
fct_setcarry[] = {
   {"F2 0", CL2_R, 41 }, { "F2 9", CL2_R, 0 },
   {"F3 0", CL3_R, 41 }, { "F3 9", CL3_R, 0 }, { } },
fct_carrywarn[] = {
   {"F2 up", CW2_L, 450 }, { "F2 down", CW2_L, 0 }, { "F2 reset", CW2_R, 20 }, { "F2 return", CW2_R, 0 }, // .4 + .05 slop from warning lever to lifter
   {"F3 up", CW3_L, 450 }, { "F3 down", CW3_L, 0 }, { "F3 reset", CW3_R, 20 }, { "F3 return", CW3_R, 0 }, { } },
fct_carry[] = {
   {"F2 add", CS2_R, -(DEGREES_PER_DIGIT + EXTRA_DEGREES_FOR_CARRY) }, {"F2 sub", CS2_R, +EXTRA_DEGREES_FOR_CARRY }, {"F2 home", CS2_R, 0 },
   {"F3 add", CS3_R, -(DEGREES_PER_DIGIT + EXTRA_DEGREES_FOR_CARRY) }, {"F3 sub", CS3_R, +EXTRA_DEGREES_FOR_CARRY }, {"F3 home", CS3_R, 0 }, { } },
fct_keepers[] = {
   {"F2 top", CSK2_R, 0 }, {"F2 bottom", CSK2_R, 90 }, {"F2 up", CSK2_L, 500 }, {"F2 mid", CSK2_L, 450 }, { "F2 down", CSK2_L, 0 },
   {"F3 top", CSK3_R, 0 }, {"F3 bottom", CSK3_R, 90 }, {"F3 up", CSK3_L, 500 }, {"F3 mid", CSK3_L, 450 }, { "F3 down", CSK3_L, 0 }, { } },
fct_test[] = { {"left", TEST_R, -90 }, {"right", TEST_R, 90 } };


//****  command parsing routines

char cmdline[CMDLENGTH], prev_cmd[CMDLENGTH] = { 0 }, prev_prev_cmd[CMDLENGTH] = { 0 };
bool saved_cmd = false;

void show_help(void) {
   char scriptnames[200];  // create a list of all the script names
   char* p = scriptnames;
   for (struct script_t* sp = named_scripts; sp->name; ++sp)
      p += sprintf(p, "%s|", sp->name);
   *(p - 1) = 0;             // remove last "|"
   const char** ptr = help;  // print all the help lines
   while (*ptr) {
      Serial.printf(*ptr++, scriptnames);
      Serial.println(); }
   Serial.print("<axle> is one of:");
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd)
      if (pmd->motor_number != NM && pmd->assigned) Serial.printf(" %s", pmd->axle_name);
   Serial.println(); }

void error(const char* msg, const char* info) {
   if (info && *info)
      Serial.printf("%s: %s\n", msg, info);
   else Serial.printf("%s\n", msg);
   got_error = true;
   clear_movements(); }

void flush_input(void) {
   //Serial.flush() flushes the *output* channel!
   while (Serial.available()) Serial.read(); }

void getstring(char* buf, unsigned buflen) {  // get a command string from the keyboard
   unsigned ndx;
   flush_input();
   Serial.print('>');
   saved_cmd = false;
   char ch;
   for (ndx = 0; ndx < buflen - 1; ++ndx) {
      while (Serial.available() == 0);  // wait for a character
      ch = Serial.read();
      Serial.print(ch);  // assume Coolterm isn't echoing
      if (ch == '\n' || ch == '\r') break;  // return: command is complete
      if (ch == '\b') {       // backspace:
         if (ndx > 0) {
            ndx -= 2;    // remove a typed character (for loop will ++ndx)
            Serial.print(" \b"); } // erase it from the screen
         else {          // except when empty, do previous previous command
            strlcpy(buf, prev_prev_cmd, buflen);
            strlcpy(prev_prev_cmd, prev_cmd, sizeof(prev_prev_cmd));
            strlcpy(prev_cmd, buf, sizeof(prev_cmd));
            saved_cmd = true;
            Serial.printf("%s\n", buf);
            return; } }
      else buf[ndx] = ch; }
   if (ndx == 0) {  // empty return: repeat last command
      strlcpy(buf, prev_cmd, buflen);
      saved_cmd = true;
      Serial.printf("%s\n", buf); }
   else {
      if (ch == '\r') Serial.println(); // if we got a CR, do a newline
      buf[ndx] = 0;
      //strlcpy(prev_prev_cmd, prev_cmd, sizeof(prev_prev_cmd));  // save prev prev command
      //strlcpy(prev_cmd, buf, sizeof(prev_cmd)); // save new one as prev command
   }
   //Serial.printf(">%s\n", buf);
}

void skip_blanks(const char** pptr) {
   while (**pptr == ' ' || **pptr == '\t' || **pptr == '\n' || **pptr == '\r') ++*pptr; }

bool scan_word(const char** pptr, char* buf, int buflen) { // scan a word up to a blank or ;
   skip_blanks(pptr);
   int ndx;
   for (ndx = 0; ndx < buflen - 1; ++ndx) {
      char chr = (*pptr)[ndx];
      if (chr == 0 || chr == ';' || chr == ' ') break;
      buf[ndx] = chr; }
   buf[ndx] = 0;
   *pptr += ndx;
   //if (debug >= 3 && ndx != 0) Serial.printf("scanned word %d characters: %s\n", ndx, buf);
   return ndx != 0; }

bool scan_key(const char** pptr, const char* keyword) { // match keyword(s) separated by blanks
   skip_blanks(pptr);
   const char* temp_ptr = *pptr;
   do {
      char matchchar = *keyword;
      if (tolower(*temp_ptr++) != tolower(*keyword++)) return false;
      if (matchchar == ' ') while (*temp_ptr == ' ') ++temp_ptr; } // blank matches multiple blanks
   while (*keyword);
   *pptr = temp_ptr;
   skip_blanks(pptr);
   return true; }

bool scan_cmd(const char** pptr, const char* keyword) { // like scan_key, but with optional save of cmd buffer
   if (scan_key(pptr, keyword)) {
      if (!saved_cmd) {
         strlcpy(prev_prev_cmd, prev_cmd, sizeof(prev_prev_cmd));  // save prev prev command
         strlcpy(prev_cmd, cmdline, sizeof(prev_cmd));  // save new one as prev command
         saved_cmd = true; }
      return true; }
   return false; }

bool scan_int(const char** pptr, int* pnum, int min, int max) { // scan an integer
   int num;
   int nch;
   if (sscanf(*pptr, "%d%n", &num, &nch) != 1
         || num < min || num > max) return false;
   *pnum = num;
   *pptr += nch;
   skip_blanks(pptr);
   return true; }

bool check_endcmd(const char** pptr) { // check if we're at the end of the command, error if not
   skip_blanks(pptr);
   if (!**pptr || **pptr == ';') return true;
   error("unknown", *pptr);
   return false; }

bool strmatch(const char* a, const char* b) {
   while (*a && *b)
      if (*a++ != *b++) return false;
   return *a == 0 && *b == 0; }

// Scan for an axle name; if it's a rotator then movement type must match
// Return the pointer to the motor descriptor, or NULL if not found.
struct motord_t* scan_axlename(const char** pptr, enum movement_t which, bool showerr) {
   const char* savep = *pptr;
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      if (pmd->motor_number != NM && scan_key(pptr, pmd->axle_name)
            && (which == ANY_MOVEMENT || pmd->motor_type == LIFT || pmd->motor_type == which)) {
         return pmd; }
      *pptr = savep; }
   if (showerr) error("bad motor", *pptr);
   return NULL; }

// Scan for a store name like S3, and return the rotator and lifter motors.
bool scan_storename(const char** pptr, int* liftmotor, int* rotatemotor) {
   if (toupper(**pptr) != 'S') {
      error("missing Sn", *pptr); return false; }
   ++ * pptr;
   int storenum;
   if (!scan_int(pptr, &storenum, 1, NUM_STORE)) {
      error("missing store number", *pptr); return false; }
   int store_lifters[NUM_STORE] = { S1_L, S2_L, S3_L, S4_L, S5_L, S6_L };
   int store_rotators[NUM_STORE] = { S1_R, S2_R, S3_R, S4_R, S5_R, S6_R };
   *liftmotor = store_lifters[storenum - 1];
   *rotatemotor = store_rotators[storenum - 1];
   return true; }

void do_homescript(void) {
   execute_commands("home"); }

void do_pause(const char** pptr) { // complete all movements and then pause
   int msec;
   while (motors_queued)
      if (!do_movements(timeunit_usec)) break;
   if (!scan_int(pptr, &msec, 1, 99999)) {
      Serial.println("waiting...");
      if (wait_for_char() == ESC) got_error = true; }
   else {
      unsigned long start_time = millis();
      flush_input();
      if (debug >= 1) Serial.printf("pausing %u msec\n", msec);
      while (millis() - start_time < (unsigned long)msec) {
         if (Serial.available()) break;
         delay(1); } } }

void do_reset(void) {  // reset our internal state, but not the hardware
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      pmd->move_queued = false;
      pmd->current_position = 0; } }

void show_state(void) {  //show the internal state of motors not at neutral or on
   for (struct motord_t* pmd = motor_descriptors; pmd->motor_number != -1; ++pmd) {
      if (pmd->motor_number != NM && pmd->assigned) {
         if (pmd->current_position != 0 || pmd->motor_state == ON)
            Serial.printf("%s (%s) is at %d and is %s\n",
                          pmd->axle_name, pmd->axle_descr, pmd->current_position, pmd->motor_state == ON ? "on" : "off"); } } }

unsigned read_switches(void) { // create a bitmap of all switch values, 15..0
   unsigned switches = 0;
   for (int switchnum = 15; switchnum >= 0; --switchnum)
      switches = (switches << 1) | (read_switch(switchnum) & 1);
   return switches; }

void show_switches(void) {  // routine to check digit wheel index hardware
   unsigned current_switches = read_switches(), new_switches;
   Serial.println("monitoring switches...");
   while (!Serial.available()) {
      if (read_switches() != current_switches) { // something changed
         delay(DEBOUNCE);
         if ((new_switches = read_switches()) != current_switches) { // see if it persists
            Serial.print("switches changed: ");
            unsigned mask = 1;
            for (int switchnum = 0; switchnum < 16; ++switchnum) {
               if ((new_switches & mask) != (current_switches & mask))
                  Serial.printf(" sw%d=%d", switchnum, new_switches & mask ? 1 : 0);
               mask <<= 1; }
            Serial.println();
            current_switches = new_switches; } } }
   Serial.println("done"); }

//***** queue a functional motor movement described by a fct_move_t structure

void do_move(struct fct_move_t* move, const char** pptr) { // queue up an elementary motion
   struct motord_t* pmd;
   int start_pct = 0, end_pct = 99;
   pmd = motor_num_to_descr[move->motor_num];
   if (!pmd) {
      error("undefined motor", NULL);
      return; }
   if (!pmd->assigned) {
      error("unassigned motor", NULL);
      return; }
   if (scan_key(pptr, "delay")) {  // scan optional timing information
      start_pct = 50; end_pct = 99; }
   else if (scan_key(pptr, "time ")) {
      if (!scan_int(pptr, &start_pct, 0, 99)
            || !scan_int(pptr, &end_pct, 1, 299)) {
         error("bad times", *pptr); return; } }
   else { // use the full time unit for this movement
      start_pct = 0; end_pct = 99; }
   if (move->distance_given)
      queue_movement(pmd, pmd->motor_type, move->position, start_pct, end_pct);  // distance to move, not position
   else {
      int desired_position = move->position;
      int distance = desired_position - pmd->current_position;
      if (distance == 0)
         Serial.printf("already there: %s\n", pmd->axle_name);
      else {
         queue_movement(pmd, pmd->motor_type, distance, start_pct, end_pct);
         pmd->current_position = desired_position; } } }

struct fct_move_t* do_function(  // parse axle name(s) and queue up a move
   struct fct_move_t* move, // an array of fct_move structures ending with one that has no keyword
   const char** pptr) {
   for (; move->keyword; ++move) {
      if (scan_key(pptr, move->keyword)) {
         if (move->position != NOMOVE) do_move(move, pptr);
         return move; } }
   error("unknown axle and keywords", *pptr);
   return NULL; }

void do_giveoff(struct fct_move_t* move, const char** pptr) {  // give off one digit on an axle finger
   for (; move->keyword; ++move) { // try each of the axles
      if (scan_key(pptr, move->keyword)) {
         struct motord_t* pmd = motor_num_to_descr[move->motor_num];
         if (!pmd) error("unassigned motor in giveoff", move->keyword);
         else {
            //if (finger->current_position == 0 && debug >= 1)  HOW TO FIND THE FINGER AXIS FOR THIS ROTATOR??
            //   Serial.printf("** warning: finger for %s not engaged\n", finger->axle_name);
            bool reverse = scan_key(pptr, "reverse");
            queue_movement(pmd, ROTATE, reverse ? -DEGREES_PER_DIGIT : DEGREES_PER_DIGIT); }
         return; } }
   error("unknown axle", *pptr);
   return; }

#if 0 // use do_function instead
struct fct_move_t* do_lockunlock(  // parse axle name to lock or unlock, and queue up the move
   struct fct_move_t* move, const char** pptr) {
   for (; move->keyword1; ++move) {
      if (scan_key(pptr, move->keyword1)) {
         do_move(move, pptr);
         return move; } }
   error("unknown axle", *pptr);
   return NULL; }
#endif

void do_onoff(enum motor_state_t onoff, const char** pptr) { // parse motor name, or none to do all motors
   struct motord_t* pmd;
   if ((pmd = scan_axlename(pptr, ANY_MOVEMENT, false)))
      power_motor(pmd, onoff); // do one motor
   else {
    bool doall = scan_key(pptr, "all");
    if (check_endcmd(pptr)) power_motors(onoff, doall); }} //  do all (or *really* all) motors

//***** the command interpreter

void do_zero(const char** pptr);

static struct script_t* find_script(const char** pptr) {
   for (struct script_t* sp = named_scripts; sp->name; ++sp)
      if (scan_key(pptr, sp->name)) return sp;
   error("unknown command or script", *pptr);
   return NULL; }

#define MAX_SCRIPTS 5   // maximum scripts that can run in parallel
#define MAX_PARMS 5     // maximum number of different #n parameters in a script line
#define MAX_PARMSIZE 20 // maximum size of each parameter replacement
#define MAX_CMDLEN 200  // maximum size of command string after parameter expansion

int substitute_parms(char* dst, const char* src, char parms[MAX_PARMS][MAX_PARMSIZE]) {
   // copy src to dst, substituting actual parameters for #1, #2, etc., and return the number of parameters substituted
   int dstndx = 0;
   int count = 0;
   while (*src) {
      if (*src == '#') { // look for #n
         char parmnum = *++src;
         if (parmnum >= '1' && parmnum <= '9') {
            ++src; // skip the parm number
            const char* parm = parms[parmnum - '1']; // actual parameter to substitute
            if (debug >= 4) Serial.printf("copying actual parm #%d: \"%s\"\n", parmnum - '1' + 1, parm);
            while (dstndx < MAX_CMDLEN && *parm) // copy it
               dst[dstndx++] = *parm++; }
         ++count; } // count the number of parameters substituted
      else if (dstndx < MAX_CMDLEN)
         dst[dstndx++] = *src++; } // copy a normal non-parm character
   dst[dstndx] = 0;
   return count; }

bool do_step_wait(void) {  // return false to abort
   Serial.print(" ...waiting");
   int chr = wait_for_char();
   if (chr == ESC) {
      got_error = true;
      return false; } // ESC terminates
   Serial.print("\b\b\b\b\b\b\b\b\b\b");  // erase "waiting"
   if (chr == '+') // convert "step" into "run"
      script_step = false;
   return true; }

struct parallel_script_t { // a script we are executing in parallel
   struct script_t* script;    // pointer to the script
   const char** next_command;  // which is the next command in its list to execute
   char parms[MAX_PARMS][MAX_PARMSIZE];  // the actual parameters to substitute for #n
};

bool do_timeunit(void) {
   if (!got_error && motors_queued > 0) {
      ++cyclenum;
      if (script_step && !do_step_wait()) return false;
      if (debug >= 1) Serial.printf("*** at time unit %d, ", cyclenum);
      do_movements(timeunit_usec); } // execute all primitive movements and movements of all the scripts in this time unit
   return true; }

static bool scan_command(const char** pptr) {
   // try to scan a single primitive command and queue the movement it requires
   if (got_error) return false;
   skip_blanks(pptr);
   // commands that save the command buffer
   if (scan_cmd(pptr, "rot ")) {  // primitive rotating motion
      struct motord_t* pmd;
      int degrees;
      if ((pmd = scan_axlename(pptr, ROTATE, true))) {
         if (scan_int(pptr, &degrees, -360 * 6, +360 * 6)) // might have 5.2:1 gearbox
            queue_movement(pmd, ROTATE, degrees);
         else error("bad degrees", *pptr); } }
   else if (scan_cmd(pptr, "lift")) {    // primitive lifting motion
      struct motord_t* pmd;
      int mils;
      if ((pmd = scan_axlename(pptr, LIFT, true))) {
         if (scan_int(pptr, &mils, -1500, +1500))
            queue_movement(pmd, LIFT, mils);
         else error("bad mils", *pptr); } }
   else if (scan_cmd(pptr, "lock1")) do_function(fct_lock1, pptr);
   else if (scan_cmd(pptr, "lock")) do_function(fct_lock, pptr);
   else if (scan_cmd(pptr, "unlock")) do_function(fct_unlock, pptr);
   //else if (scan_cmd(pptr, "weaklock")) do_function(fct_weaklock, pptr);
   else if (scan_cmd(pptr, "mesh")) do_function(fct_mesh, pptr);
   else if (scan_cmd(pptr, "unmesh")) do_function(fct_unmesh, pptr);
   else if (scan_cmd(pptr, "finger")) do_function(fct_finger, pptr);
   else if (scan_cmd(pptr, "nofinger")) do_function(fct_nofinger, pptr);
   else if (scan_cmd(pptr, "shift")) do_function(fct_shift, pptr);
   else if (scan_cmd(pptr, "do_zero")) do_zero(pptr); // do_zero {An{top|bot}|Fn|Sn|RR} [calibrate]
   else if (scan_cmd(pptr, "giveoff")) do_giveoff(fct_giveoff, pptr);
   else if (scan_cmd(pptr, "setcarry")) do_function(fct_setcarry, pptr);
   else if (scan_cmd(pptr, "carrywarn")) do_function(fct_carrywarn, pptr);
   else if (scan_cmd(pptr, "carry")) do_function(fct_carry, pptr);
   else if (scan_cmd(pptr, "keepers")) do_function(fct_keepers, pptr);
   //else if (scan_cmd(pptr, "test")) do_function(fct_test, pptr);
   else if (scan_cmd(pptr, "test")) do_test();
   else if (scan_cmd(pptr, "repeat ")) {
      int repeatcount = 9999;
      scan_int(pptr, &repeatcount, 1, 9999);
      while (--repeatcount) execute_commands(*pptr); }
   // commands that don't save the command buffer; they call scan_key instead of scan_cmd
   else if (scan_key(pptr, "timeunit ")) {
      int timeunit_msec;
      if (scan_int(pptr, &timeunit_msec, 10, 60 * 1000))
         timeunit_usec = timeunit_msec * 1000L;
      else error("bad time in msec", *pptr); }
   else if (scan_key(pptr, "timeunit")) Serial.printf("%d msec\n", timeunit_usec / 1000);
   else if (scan_key(pptr, "tu")) timeunit_usec = 157 * 1000; // secret shortcut to set Babbage's time unit
   else if (scan_key(pptr, "debug ")) {
      if (!scan_int(pptr, &debug, 0, 99)) error("bad debug level", *pptr); }
   else if (scan_key(pptr, "debug")) Serial.printf("debug %d\n", debug);
   else if (scan_key(pptr, "on")) do_onoff(ON, pptr);
   else if (scan_key(pptr, "off")) do_onoff(OFF, pptr);
   else if (scan_key(pptr, "home")) do_homescript();
   else if (scan_key(pptr, "pause")) do_pause(pptr);
   else if (scan_key(pptr, "reset")) do_reset();
   else if (scan_key(pptr, "switches")) show_switches();
   else if (scan_key(pptr, "motors")) show_motors();
   else if (scan_key(pptr, "state")) show_state();
   else if (scan_key(pptr, "calibrate")) do_calibrate(pptr);
   else if (scan_key(pptr, "bell")) Serial.print(BELL);
   else if (scan_key(pptr, "restart")) SCB_AIRCR = 0x05FA0004; // Teensy processor reset
   else if (scan_key(pptr, "help")) show_help();
   else if (scan_key(pptr, "?")) show_help();
   else return false;
   scan_key(pptr, ";");
   return true; }

void execute_commands(const char* ptr, int level) { // can be called recursively
   // execute all the commands in a string simultaneously, including running
   // in parallel any embedded "run" commands that execute multi-step scripts
   struct parallel_script_t parallel_scripts[MAX_SCRIPTS];
   int num_scripts = 0;
   skip_blanks(&ptr);
   if (debug >= 2 && level > 1) Serial.printf("executing at level %d: \"%s\"\n", level, ptr);
   // scan a sequence of primitive commands or run/step script-starting commands,
   // all of which execute in parallel
   while (!got_error && *ptr) {
      if (!scan_command(&ptr)) { // first try to parse a primitive command
         if (scan_cmd(&ptr, "step ")) { // if not, try for a script
            if (level == 1) script_step = true; }
         else {
            scan_cmd(&ptr, "run ");  // now "run" is optional because any script can be a command
            if (level == 1) script_step = false; }
         script_t* sp = find_script(&ptr); // add to the list of parallel running scripts
         if (sp) { // found the script
            parallel_scripts[num_scripts].script = sp;
            parallel_scripts[num_scripts].next_command = sp->commands;
            if (debug >= 3) Serial.printf("starting script \"%s\" with command \"%s\"\n", sp->name, sp->commands[0]);
            for (int parmndx = 0; parmndx < MAX_PARMS; ++parmndx) // parse and store all the parameters; unused ones are null
               scan_word(&ptr, parallel_scripts[num_scripts].parms[parmndx], MAX_PARMSIZE);
            ++num_scripts; scan_key(&ptr, ";"); } } }
   // All the movements for primitive commands have been queued, and the scripts have been saved.
   // Now repeatedly execute one line of each of the scripts running in parallel at this level
   int running_scripts = num_scripts;
   while (running_scripts > 0 && !got_error) {
      for (int scriptnum = 0; scriptnum < num_scripts; ++scriptnum) // do one command from each active script
         if (*parallel_scripts[scriptnum].next_command) { // this script is still running
            char command[MAX_CMDLEN]; // do parameter substitution of all #n
            int num_substitutions = substitute_parms(command, *parallel_scripts[scriptnum].next_command, parallel_scripts[scriptnum].parms);
            if (num_substitutions > 0 && debug >= 3)
               Serial.printf("substituted %d parameters in script \"%s\" command \"%s\"\n",
                             num_substitutions, parallel_scripts[scriptnum].script->name, *parallel_scripts[scriptnum].next_command);
            execute_commands(command, level + 1); // scan commands in the expanded script line, which could contain other "run <script>" commands
            if (!*++parallel_scripts[scriptnum].next_command) --running_scripts; // this script has now ended
         }
      if (running_scripts > 0)
         if (!do_timeunit()) return; } // do movements and continue the scripts
   if (level == 1) do_timeunit(); } // do leftover movements

void execute_commands(const char* ptr) { // execute top-level command
   execute_commands(ptr, 1); }

//*
