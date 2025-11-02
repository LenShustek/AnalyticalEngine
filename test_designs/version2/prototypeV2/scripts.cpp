#include "prototype.h"

// predefined scripts

#define SCRIPT static const char *

static const char* read_script[] = { // read s {top|bot} a {top|bot}
   "mesh S#1 #2 finger; mesh RR top rack; mesh RP#3 A#3 #4; mesh MP#3 A#3 #4; unlock A#3 #4; unlock MP#3; unlock FP#3;",
   "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1",
   "unmesh S#1; unmesh RR; unmesh MP#3 A#3; lock MP#3; lock FP#3; lock A#3 delay;",
   "giveoff S#1; unmesh RP#3;", NULL };

static const char* readonly_script[] = { // readonly s {top|bot}
   "mesh S#1 #2 finger; mesh RR top rack; mesh RP2 MP2; unlock MP2; unlock FP2; ", // RP-MP-FP is only to create drag
   "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1", "giveoff S#1",
   "unmesh S#1; unmesh RR; unmesh RP2; lock MP2; lock FP2;",
   "giveoff S#1;", NULL };

static const char* write_script[] = { // write s {top|bot} a {top|bot}
   "mesh S#1 #2 rack; mesh RR top rack; mesh RP#3 A#3 #4; mesh MP#3 A#3 #4; finger A#3 #4; unlock A#3 #4; unlock MP#3; unlock FP#3;",
   "giveoff A#3", "giveoff A#3", "giveoff A#3", "giveoff A#3", "giveoff A#3", "giveoff A#3", "giveoff A#3", "giveoff A#3", "giveoff A#3",
   "nofinger A#3; lock A#3; lock MP#3; lock FP#3;",
   "unmesh S#1; unmesh RR; unmesh MP#3 A#3; giveoff A#3; unmesh RP#3;", NULL };

static const char* restore_script[] = { // restore the rack after writing
   "mesh RR top finger;",
   "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR", "giveoff RR",
   "unmesh RR",
   "giveoff RR", NULL };

static const char* revrestore_script[] = { // reverse restore the rack after reading
   "mesh RR top finger;",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "unmesh RR", NULL };

static const char* rewrite_script[] = { // rewrite s top|bot (reverse restore after reading and retain)
   " mesh S#1 #2 rack; mesh RR top finger;",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse", "giveoff RR reverse",
   "unmesh S#1; unmesh RR", NULL };

static const char *zeroF_script[] = { // zeroF n [calibrate]
   "finger F#1; mesh FC#1;",
   "unlock FP#1; unlock MP#1",
   "do_zero F#1 #2",
   "unmesh FC#1; lock FP#1; lock MP#1",
   "nofinger F#1; carrywarn F#1",
   "giveoff F#1; carrywarn F#1 return", NULL };

static const char *zeroA_script[] = { // zeroA n [top|bot] [calibrate]
   "finger A#1 #2; mesh MP#1 A#1 #2;",
   "unlock A#1 #2; unlock MP#1; unlock FP#1",
   "do_zero A#1 #3", // do the zero or the calibration
   "nofinger A#1; unmesh MP#1 A#1",
   "lock A#1; lock MP#1; lock FP#1",
   "giveoff A#1;", NULL };

static const char *zeroS_script[] = { // zeroS n [top|bot] [calibrate]
   "mesh S#1 #2 finger; mesh RP2 MP2; unlock MP2; unlock FP2;", // RP-MP-FP is only to create drag
   "do_zero S#1 #3", // do the zero or the calibration
   "unmesh RP2;", "lock MP2;", " lock FP2 delay;", // do while S is still meshed with the rack
   "unmesh S#1;",
   "giveoff S#1", NULL };

static const char *zeroRR_script[] = { // zeroS [top|bot] [calibrate]
   "mesh RR #1 finger;",
   "do_zero RR #2", // do the zero or the calibration
   "unmesh RR",
   "giveoff RR", NULL };

static const char *home_script[] = {
   // reset everything to initial positions
   #if !SMALL_PROTOTYPE
   "lock F; unmesh FC; nofinger F; setcarry nowarn time 0 199; keepers top;",
   #endif
   "lock A1; lock A2; lock FP; lock MP; nofinger A; unmesh FPC; unmesh MPC; shift down;",
   #if !SMALL_PROTOTYPE
   "setcarry 9 time 0 199; keepers down; carrywarn down;",
   #endif
   NULL };

static const char* a2tb_script[] = { // move A2 top to bottom
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

static const char* f2a2t_script[] = { // move F2 to A2 top
   //"finger F; mesh FC; mesh MPC A1; weaklock F delay; unlock A1 delay; unlock FP delay;",
   "finger F2; mesh FC2; mesh MP2 A2 top; ",
   "unlock FP2; unlock MP2; unlock A2 top;",
   "giveoff F2", "giveoff F2", "giveoff F2", "giveoff F2", "giveoff F2", "giveoff F2", "giveoff F2", "giveoff F2", "giveoff F2",
   "lock FP2; lock MP2 delay",
   "lock A2; nofinger F2;",
   "unmesh FC2; unmesh MP2 A2; giveoff F2", NULL };

static const char *add1c_script[] = {
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

static const char *add_script[] = {
   // add the number on A1 to F in 18 time units
   // assume "keepers down" and "keepers top" to start
   "finger A1; mesh FC; mesh MPC A1; keepers mid;",
   "unlock A1; unlock FP delay; unlock MP delay; unlock F delay; ",
   "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A",
   "lock A1; lock MP delay;", // sequential locking
   "lock FP; lock F delay; nofinger a; unmesh FC; unmesh MPC;",
   "carrywarn up;", // raise carry sector wheels
   "giveoff A; keepers bottom time 0 74; keepers up time 75 99;", // support carry sector wheels
   "carrywarn down; weaklocklock F delay;", // get wires out of the way and prepare to carry
   "carry add;", // do the carries, which may create additional warns
   "lock F; keepers top delay; setcarry nowarn time 50 199;", // do keepers top and nowarn only after F is locked
   "keepers down;", // force carry sectors to disengage
   "setcarry 9 time 0 149; carry home;",  // restore wires to carry 9 position
   NULL };

static const char *sub2c_script[] = {
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

static const char *sub_script[] = {
   // subtract the number on A1 from F in 17 time units
   // assume "keepers down" and "keepers top" to start
   "finger A1; mesh FC; mesh FPC A1; keepers mid;",
   " unlock A1; unlock FP delay; unlock MP delay;  unlock F delay; setcarry 0; carry add;",
   "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A",
   "lock A1; lock FP delay; lock MP delay;", // sequential locking
   "lock F; nofinger a; unmesh FC; unmesh FPC;",
   "carrywarn up;",
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

static const char *shl_script[] = {
   "finger A2; mesh FPC A1; mesh MPC A2",
   "lock1 FP; unlock A1; unlock A2; unlock MP"
   "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A", "giveoff A",
   "lock A2;", // also MP delay
   "lock FP; lock MP delay; lock A1 delay",
   "nofinger A2; unmesh FPC; unmesh MPC", NULL };

struct script_t named_scripts[] = {
   { "readonly", readonly_script },
   { "read", read_script },
   { "write", write_script },
   { "restore", restore_script },
   { "revrestore", revrestore_script },
   { "rewrite", rewrite_script },
   { "zeroF", zeroF_script },
   { "zeroA", zeroA_script },
   { "zeroS", zeroS_script },
   { "zeroRR", zeroRR_script },
   { "home", home_script },
   { "a2tb", a2tb_script },
   { "a2bf2", a2bf2_script },
   { "f2a2t", f2a2t_script },
   { "add1c", add1c_script },
   { "add", add_script },
   { "sub2c", sub2c_script },
   { "sub", sub_script },
   { "fibone", fibone_script },
   { "fib", fib_script },
   { "shl", shl_script },
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
