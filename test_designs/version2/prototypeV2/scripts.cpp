#include "prototype.h"

// predefined scripts

#define SCRIPT static const char *

// read from Store to one of the Mill registers
static const char* read_script[] = { // read Sn {top|bot} Am {top|bot}
   "mesh S#1 #2 finger; mesh RR top rack; mesh SIGN rack; mesh RP#3-A #3 #4; mesh MP#3-A #3 #4;",
   "unlock #3 #4; unlock MP#3-A; unlock FP#3-A; unlock R;",
   "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1",
   "unmesh S#1; unmesh SIGN; unmesh RR; lock MP#3-A; ",
   "unmesh MP#3-A #3; lock FP#3-A; lock R; lock #3 delay;",
   "giveoff S#1; unmesh RP#3-A;", NULL };

// zero a Store number by reading it  NEEDS WORK
static const char* readonly_script[] = { // readonly s {top|bot}
   "mesh S#1 #2 finger; mesh RR top rack; mesh RP2 MP2; unlock MP2; unlock FP2; unlock R; ", // RP2-MP2-FP2 is only to create drag
   "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1",
   "unmesh S#1; unmesh RR; unmesh RP2; lock MP2; lock FP2; lock R;",
   "giveoff S#1;", NULL };

// write to Store from one of the Mill registers
static const char* write_script[] = { // write Sn {top|bot} Am {top|bot}
   "mesh S#1 #2 rack; mesh RR top rack; mesh RP#3-A #3 #4; mesh MP#3-A #3 #4; finger #3 #4; mesh SIGN finger; unlock #3 #4; unlock MP#3-A; unlock FP#3-A; unlock R;",
   "giveoff #3; giveoff SIGN;",  "giveoff #3; giveoff SIGN;", "giveoff #3; giveoff SIGN;" , "giveoff #3; giveoff SIGN;",
   "giveoff #3; giveoff SIGN;",  "giveoff #3; giveoff SIGN;", "giveoff #3; giveoff SIGN;", "giveoff #3; giveoff SIGN;", "giveoff #3; giveoff SIGN;",
   "nofinger #3; lock R; lock #3;",
   "lock MP#3-A;",
   "lock FP#3-A; unmesh S#1; unmesh SIGN; unmesh RR; unmesh MP#3-A #3; giveoff #3; unmesh RP#3-A;", NULL };

static const char* restorewrite_script[] = { // restore the rack after writing
   "mesh RR top finger; mesh RP2 MP2; mesh SIGN rack; ", // RP2-MP2-FP2 and SIGN is only to create drag
   "unlock MP2; unlock FP2; unlock R;",
   "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR",
   "lock R; lock MP2; lock FP2",
   "unmesh RR; unmesh RP2; unmesh SIGN;",
   "giveoff RR", NULL };

static const char* restoreread_script[] = { // restore the rack after reading
   "giveoff RR 24 reverse", // takeup one digit (normally 360/20=18)
   "mesh RR top finger; mesh RP2 MP2; mesh SIGN rack;",  // RP2-MP2-FP2 and SIGN is only to create drag
   "unlock MP2; unlock FP2; unlock R",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "lock R; lock MP2; lock FP2;",
   "unmesh RR; unmesh RP2; unmesh SIGN;",
   "giveoff RR 6",  NULL };

// restore the rack after reading, and write the number back to the Store ("giveoff and retain")
static const char* rewrite_script[] = { // rewrite s top|bot
   "giveoff RR reverse",
   "mesh S#1 #2 rack; mesh RR top finger; unlock R; ",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "lock R; unmesh S#1; unmesh RR", NULL };

static const char* writeread_script[] = { // write, restore, read, restore
#define DOPAUSE ""
//#define DOPAUSE "pause",
   "pause 2000;",
   "write s1 top a2 top", DOPAUSE
   "restore write",       DOPAUSE
   "read s1 top a2 top",  DOPAUSE
   "restore read", NULL };

static const char* zeroF_script[] = { // zero F n [calibrate]
   "finger F#1; mesh REV#1 in;", // long pinions create drag
   "unlock FP#1; unlock MP#1",
   "do_zero F#1 #2",
   "unmesh REV#1; lock FP#1; lock MP#1",
   "nofinger F#1; carrywarn F#1 reset",
   "giveoff F#1; carrywarn F#1 return", NULL };

static const char* zeroA_script[] = { // zero An [top|bot] [calibrate]
   "finger A#1 #2; mesh MP#1 A#1 #2;",
   "unlock A#1 #2; unlock MP#1; unlock FP#1",
   "do_zero A#1 #3", // do the zero or the calibration
   "nofinger A#1; unmesh MP#1 A#1",
   "lock A#1; lock MP#1; lock FP#1",
   "giveoff A#1;", NULL };

static const char* zeroS_script[] = { // zero Sn [top|bot] [calibrate]
   "mesh S#1 #2 finger; mesh RP2 MP2; mesh SIGN rack; unlock MP2; unlock FP2; unlock R;", // RP-MP-FP and SIGN is only to create drag
   "do_zero S#1 #3", // do the zero or the calibration
   "lock R;",
   "unmesh RP2; unmesh SIGN;", "lock MP2;", "lock FP2 delay;", // do while S is still meshed with the rack
   "unmesh S#1;",
   "giveoff S#1; unlock R;",
   "pause restore rack",
   "lock R;", NULL };

static const char* zeroRR_script[] = { // zero RR [top|bot] [calibrate]
   "mesh RR #1 finger; mesh RP2 MP2; mesh SIGN rack; unlock MP2; unlock FP2; unlock R;", // RP-MP-FP and SIGN is only to create drag
   "do_zero RR #2", // do the zero or the calibration
   "unmesh RP2; unmesh SIGN;", "lock MP2;", "lock FP2 delay;", // do while S is still meshed with the rack
   "unmesh RR;",
   "giveoff RR;", // move to other side of nib
   "pause restore rack",
   "lock R;", NULL };

static const char* zeroSIGN_script[] = { // zero SIGN [calibrate]
   "mesh SIGN finger; unlock R;",
   "do_zero SIGN #1", // do the zero or the calibration
   "unmesh SIGN;",
   //"giveoff SIGN;", // move to other side of nib
   "pause restore rack",
   "lock R;", NULL };

static const char* SetS_script[] = { // set Sn [top|bot]
   "mesh S#1 #2 rack; unlock R;",
   "pause set wheel", // allow wheel to be set
   "unmesh S#1;",
   "pause restore rack", // allow rack to be restored
   "lock R", NULL
};

static const char* SetA_script[] = { // set An [top|bot]
   "unlock A#1 #2;",
   "pause set wheel", // allow wheel to be set
   "lock A#1", NULL
};

static const char* SetF_script[] = { // set Fn
   "unlock F#1;",
   "pause set wheel", // allow wheel to be set
   "lock F#1", NULL
};

static const char* home_script[] = {
   // reset everything to initial positions
   "lock A2; lock MP2; lock FP2; lock R;",
   "nofinger A2; nofinger F2; shift MP2 down;",
   "setcarry F2 9; carrywarn F2 down; carrywarn F2 return; keepers F2 down; keepers F2 top;",
   "unmesh FP2 A2; unmesh MP2 A2; unmesh S1; unmesh s2; unmesh RR; unmesh SIGN; unmesh RP2; unmesh FC2; unmesh REV2;",  NULL };

static const char* add_script[] = { // add An [top|bot]
   // assume "keepers down" and "keepers top" to start
   "finger A#1 #2; mesh FC#1; mesh REV#1 lock; mesh MP#1 A#1 #2; keepers F#1 mid;",
   "unlock A#1 #2; unlock FP#1 delay; unlock MP#1 delay;",
   "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1",
   "lock A#1; lock MP#1 delay;", // sequential locking
   "lock FP#1; nofinger A#1; unmesh FC#1; unmesh REV#1; unmesh MP#1 A#1;",
   "carrywarn F#1 up;", // raise carry sector wheels
   "runupcheck; giveoff A#1; keepers F#1 bottom;", // support carry sectors
   //"keepers F#1 up time 75 99; ", // support carry sector wheels
   "carrywarn F#1 down;", // get wires out of the way and prepare to carry
   "carry F#1 add;", // do the carries, which may create additional warns
   "keepers F#1 top delay; carrywarn F#1 reset;", // do keepers top and nowarn
   "keepers F#1 down;", // force carry sectors to disengage
   "carry F#1 home; carrywarn F#1 return",
   NULL };

static const char* sub_script[] = { // sub An [top|bot]
   // assume "keepers down" and "keepers top" to start
   "finger A#1 #2; mesh REV#1 in; mesh MP#1 A#1 #2; keepers F#1 mid;",
   "unlock A#1 #2; unlock FP#1 delay; unlock MP#1 delay;  setcarry F#1 0; carry F#1 add;",
   "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1", "giveoff A#1",
   "lock A#1; lock MP#1 delay;", // sequential locking
   "lock FP#1; nofinger A#1; unmesh REV#1; unmesh MP#1 A#1;",
   "carrywarn F#1 up;", // raise carry sector wheels
   "runupcheck; giveoff A#1; keepers F#1 bottom;", // support carry sectors
   //"keepers F#1 up time 75 99; ", // support carry sector wheels
   "carrywarn F#1 down;", // get wires out of the way and prepare to borrow
   "carry F#1 sub;", // do the borrows, which may create additional warns
   "keepers F#1 top delay; carrywarn F#1 reset;", // do keepers top and nowarn
   "keepers F#1 down; ", // force carry sectors to disengage
   "setcarry F#1 9; carrywarn F#1 return;", // restore wires to carry 9 position
   NULL };

static const char* load_script[] = { // load An [top|bot]  (from Fn)
   "finger F#1; mesh FC#1; mesh MP#1 A#1 #2;",
   "unlock FP#1; unlock MP#1; unlock A#1 #2 delay;",
   "giveoff F#1", "giveoff F#1", "giveoff F#1", "giveoff F#1", "giveoff F#1", "giveoff F#1", "giveoff F#1", "giveoff F#1", "giveoff F#1",
   "lock MP#1; lock FP#1 delay",
   "lock A#1; nofinger F#1;",
   "unmesh FC#1; unmesh MP#1 A2; giveoff F#1", NULL };

static const char* countertest_script[] = {
   "ctr 2 top",
   "ctr 2 up", "ctr 2 up", "ctr 2 up", "ctr 2 up", "ctr 2 up",
   "rot ctr2r -2", // backlash compensation
   "repeat switchtest ctr2 stoprepeat; ctr 2 down;",
   "ctr 2 bot; rot ctr2r 2;", NULL };

static const char* decimaltest_script[] = {
   "ctr 1 top; ctr 2 mid;",
   "repeat switchtest ctr1 stoprepeat; ctr 1 down;",
   "ctr 2 top; ctr 1 mid;",
   "repeat switchtest ctr2 stoprepeat; ctr 2 down;",
   "ctr 1 bot; ctr 2 bot;", NULL };

static const char* testgiveoff_script[] = {
   "mesh FC2; mesh FP2 A2 top;",
   "unlock A2 top; unlock FP2; unlock MP2;",
   "finger A2 top;", NULL };

#if 0 // scripts not converted yet
static const char* a2tb_script[] = { // move A2 top to bottomF
   "finger A2 top; mesh MP2 A2 top; mesh FP2 A2 bot;",
   "unlock A2; unlock MP2; unlock FP2;",
   "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2",
   "lock A2 top; lock MP2 delay;", // consecutive locking!
   "lock FP2; lock A2 delay; nofinger A2;",
   "unmesh MP2 A2; unmesh FP2 A2; giveoff A2", NULL };

static const char* a2bf2_script[] = { // move A2 bottom to F2
   "finger A2 bot; mesh FC2; mesh MP2 A2 bot;",
   "unlock A2 bot; unlock FP2 delay; unlock MP2 delay",
   "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2",
   "lock A2; lock MP2 delay;", // consecutive locking
   "lock FP2;"
   "nofinger A2; unmesh FC2; unmesh MP2 A2;",
   "giveoff A2", NULL };

static const char* add1c_script[] = {
   // assume "keepers down" and "keepers top" to start
   "finger A1; mesh FC; mesh MPC A1; mesh FPC A2; keepers mid;",
   "unlock A1; unlock FP delay; unlock MP delay; unlock F delay; unlock A2 delay; ",
   "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A",
   "lock A1; lock A2; lock MP delay;", // sequential locking
   "lock FP; lock F delay; nofinger a;",
   "unmesh FC; unmesh MPC; unmesh FPC;",
   "carrywarn up;", // raise carry sector wheels
   "giveoff A; keepers bottom time 0 74; keepers up time 75 99;", // support carry sector wheels
   "carrywarn down; weaklock F delay;", // get wires out of the way and prepare to carry
   "carry add;", // do the carries, which may create additional warns
   "lock F; keepers top delay; setcarry nowarn time 50 199;", // do keepers top and nowarn only after F is locked
   "keepers down;", // force carry sectors to disengage
   "setcarry 9 time 0 149; carry home;",  // restore wires to carry 9 position
   NULL };

static const char* sub2c_script[] = {
   // subtract the number on A2 from F and copy to A1
   // assume "keepers down" and "keepers top" to start
   "finger A2; mesh FC; mesh FPC A2; mesh MPC A1; keepers mid;",
   " unlock A2; unlock FP delay; unlock MP delay; unlock F delay; unlock A1 delay;  setcarry 0; carry add;",
   "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A",
   "lock A1; lock FP delay; lock MP delay;", // sequential locking
   "lock A2; lock F; nofinger a; unmesh FC; unmesh FPC; unmesh MPC;",
   "carrywarn up;", // raise carry sector wheels
   "giveoff A; keepers bottom time 0 74; keepers up time 75 99;", // support carry sector wheels
   "carrywarn down; weaklock F delay;", // get wires out of the way and prepare to borrow
   "carry sub;", // do the borrows, which may create additional warns
   "lock F; keepers top delay; setcarry nowarn time 50 199;", // do keepers top and nowarn only after F is locked
   "keepers down; ", // force carry sectors to disengage
   "setcarry 9 time 0 149; carry home;", // restore wires to carry 9 position
   NULL };

static const char* fibone_script[] = {
   // compute the next Fibonacci number
   // assumes FIB(n) is on A2 top, FIB(n-1) is on F2, and A2 bot is zero
   //**cycle 1: add A2 top to F while simultaneously copying it to A2 bot
   "finger A2 top; mesh FC2; mesh MP2 A2 top; mesh FP2 A2 bot; keepers F2 mid;",
   "unlock FP2; unlock MP2; unlock A2 delay;",
   "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2", "giveoff A2",
   "lock A2 top; lock MP2 delay;",
   "lock FP2; lock A2 delay;",
   "nofinger A2; unmesh FC2; unmesh MP2 A2; unmesh FP2 A2; carrywarn F2 up;",
   "giveoff A2; keepers F2 bottom time 0 74; keepers F2 up time 75 99;",
   "carrywarn F2 down;",
   "carry F2 add ",
   "keepers F2 top; carrywarn F2 reset;",
   "keepers F2 down; carrywarn F2 return;",
   //**cycle 2: move F2 to A2 top
   "run f2a2t",
   //**cycle 3: move A2 bot to F2
   "run a2bf2;",
   "bell; pause 1000",
   NULL };

static const char* fib_script[] = {
   // compute the first 19 Fibonacci numbers
   // 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765
   "run zeroA 2 top;", // set everything to zero
   "run zeroA 2 bot; run zeroF 2",
   //set A2 top to 1 by moving the finger backwards
   "finger A2 top; unlock A2 top delay;",
   "giveoff A2 reverse;",
   "nofinger A2; lock A2;",
   "giveoff A2;", // restore finger to normal position
   "run fibone", "run fibone", "run fibone", "run fibone", "run fibone", "run fibone",
   "run fibone", "run fibone", "run fibone", "run fibone", "run fibone", "run fibone",
   "run fibone", "run fibone", "run fibone", "run fibone", "run fibone", "run fibone", "run fibone", NULL };

static const char* shl_script[] = {
   "finger A2; mesh FPC A1; mesh MPC A2",
   "lock1 FP; unlock A1; unlock A2; unlock MP"
   "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A",
   "lock A2;", // also MP delay
   "lock FP; lock MP delay; lock A1 delay",
   "nofinger A2; unmesh FPC; unmesh MPC", NULL };
#endif

struct script_t named_scripts[] = { // true: don't show, because there is a help line for it
   { "readonly s", readonly_script, true },
   { "read s", read_script, true },
   { "write s", write_script, true },
   { "rewrite s", rewrite_script, true },
   { "writeread", writeread_script, false },
   { "restore read", restoreread_script, false },
   { "restore write", restorewrite_script, false },
   { "zero F", zeroF_script, true },
   { "zero A", zeroA_script, true },
   { "zero SIGN", zeroSIGN_script, true },
   { "zero S", zeroS_script, true },
   { "zero RR", zeroRR_script, true },
   { "set S", SetS_script, true },
   { "set A", SetA_script, true },
   { "set F", SetF_script, true },
   { "home", home_script, false },
   { "add a", add_script, true },
   { "sub a", sub_script, true },
   { "load a", load_script, true },
   { "countertest", countertest_script },
   { "decimaltest", decimaltest_script },
   { "testgiveoff", testgiveoff_script },
   #if 0 // scripts not converted yet
   { "a2tb", a2tb_script },
   { "a2bf2", a2bf2_script },
   { "f2a2t", f2a2t_script },
   { "add1c", add1c_script },
   { "sub2c", sub2c_script },
   { "fibone", fibone_script },
   { "fib", fib_script },
   { "shl", shl_script },
   #endif

   #if 0 // tests for parallel execution of scripts
   {
      "test2", SCRIPT {
         "rot st1r 1",
         "rot st1r 2; run S2;",
         NULL } },
   {
      "s2", SCRIPT {
         "run s3; rot rrr 3",
         "rot rrr 4",
         NULL } },
   {
      "s3", SCRIPT {
         "rot br 5",
         "rot br 6",
         "run s4",
         NULL } },
   {
      "s4", SCRIPT {
         "lift bl 7",
         "lift bl 8",
         NULL } },
   {
      "restore", SCRIPT {
         "rot br 1",
         "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR",
         "rot br -1",
         NULL } },
   {
      "copynum", SCRIPT {
         "lift #2 5",
         "giveoff #1", "giveoff #1", "giveoff #1", "giveoff #1", "giveoff #1", "giveoff #1", "giveoff #1", "giveoff #1", "giveoff #1",
         "lift #2 -5",
         NULL } },
   {
      "test", SCRIPT {
         "rot st1r 1",
         "run restore; run copynum b bl;",
         "rot st1r -1",
         NULL } },
   #endif //tests for parallel execution of scripts

   // add more scripts here...
   { NULL } };

// high-level command procedures
// (Easier to do in C than to invent more scripting language primitives.)

static bool F2pos; // an internal state variable that keeps track of the carriage sign
#define SIGN_POS 1

void chainadd_proc (const char* var) {
   execute_commands ("read %s A2 top", var); // read the value to be added into A2
   if (F2pos) { // carriage is positive
      if (read_switch (SW_SIGN) == SIGN_POS) { // new number is positive
         Serial.println("add pos to pos");
         execute_commands ("add A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) Serial.println("overflow"); }
      else { //new number is negative
         Serial.println("add neg to pos");
         execute_commands ("sub A2 top; restore read");
         if (read_switch (F2_RUNUP) == 0 ) F2pos = false; } }
   else { // carriage is negative
      if (read_switch (SW_SIGN) == SIGN_POS) { // new number is positive
         Serial.println("add pos to neg");
         execute_commands ("add A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) F2pos = true; }
      else { // new number is negative
         Serial.println("add neg to neg"); 
         execute_commands ("sub A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) Serial.println("overflow"); } } }

void chainsub_proc (const char* var) {
   execute_commands ("read %s A2 top", var); // read the value to be added into A2
   if (F2pos) { // carriage is positive
      if (read_switch (SW_SIGN) != SIGN_POS) { // new number is negative
         Serial.println("sub neg from pos");
         execute_commands ("add A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) Serial.println("overflow"); }
      else { //new number is positive
         Serial.println("sub pos from pos");
         execute_commands ("sub A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) F2pos = false; } }
   else { // carriage is negative
      if (read_switch (SW_SIGN) != SIGN_POS) { // new number is negative
         Serial.println("sub neg from neg");
         execute_commands ("add A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) F2pos = true; }
      else { // new number is positive
         Serial.println("sub pos from neg");
         execute_commands ("sub A2 top; restore read;");
         if (read_switch (F2_RUNUP) == 0 ) Serial.println("overflow"); } } }

void writeback_proc (const char* var) {
   execute_commands ("load A2 top");
   if (not F2pos) { // carriage is negative, so negate the number before writing back
      execute_commands ("sub A2 top"); F2pos = true;
      execute_commands ("load A2 top"); }
   execute_commands ("write %s A2 top", var);
   execute_commands ("restore write;"); }

void chaintest_proc (void) {
   F2pos = true;
   chainadd_proc ("s1 top");
   chainsub_proc ("s1 bot");
   writeback_proc ("s2 top"); }

   //*