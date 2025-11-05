/* prototype.h
 debug values:
  0 nothing
  1 UI level summary
  2 overall motor overall movement report; parsing overview
  3 individual motor movement report; parsing info
  4 schedules and start/stop of motor movements
  5 every move of every motor
  6 every step of every motor
  */
#define MULDIV_PROTOTYPE false      // multiply/divider: three digit stacks, three sets of long pinions, two carriages, and counters
#define NUM_STORE 6                 // number of store axles, not including rack restorer
#define uSTEPS_PER_STEP 4           // how many microsteps per step the drivers are configured for (MODE1 high)
#define DIGIT_REPETITIONS 2         // number of repetitions of 0-9 on each wheel
#define DEFAULT_TIMEUNIT_MSEC 500   // default time unit for moving one digit (157 for Plans 16-28)
#define DEBOUNCE 25                 // switch debounce time in msec
#define CMDLENGTH 150

// the time to move one degree is computed to have the same circumferential speed as moving one digit
#define timeunit_degree_usec (timeunit_usec * 10 * DIGIT_REPETITIONS / 360)

#include "Arduino.h"
#include <limits.h>
#define BELL '\x0a'
#define ESC  '\x1b'
#define DEL  '\x7f'
#define HOME '\x01'
#define END  '\x04'

#define uSTEPS_PER_ROTATION (uSTEPS_PER_STEP * STEPS_PER_ROTATION)
#define DEGREES_PER_DIGIT (360 / 10 / DIGIT_REPETITIONS)
#define EXTRA_DEGREES_FOR_CARRY 5 // backlash, and carry wheels are smaller

// Motors are *declared* here by assigning motor numbers from 0..95.
// Motors are *defined* in motors.cpp by allocating a motor_descriptor (see below) for them.
// Motors are *assigned* physical positions on the boards by setmotor() in motors.cpp;
// that an opportunity to have the motor cables reach the boards with minimum tangles.
enum motornum_t {
   F2_R,      //0 carriage wheel finger rotate (0 can't be a lifter)
   F2_L,      //1 carriage wheel finger lift
   F3_L,      //2 carriage wheel finger lift
   F3_R,      //3 carriage wheel finger rotate
   A1_L,      //4 A figure wheel finger lift
   A1_R,      //5 A figure wheel finger rotate
   A2_L,      //6 A figure wheel finger lift
   A2_R,      //7 A figure wheel finger rotate
   A3_L,      //8 A figure wheel finger lift
   A3_R,      //9 A figure wheel finger rotate
   A1K_L,     //10 A figure wheel lock lift
   A2K_L,     //11 A figure wheel lock lift
   A3K_L,     //12 A figure wheel lock lift
   FC2_L,     //13 carriage wheel connector lift
   REV2_L,    //14 reversing gear lift
   FC3_L,     //15 carriage wheel connector lift
   REV3_L,    //16 reversing gear lift
   MP1_L,     //17 movable long pinion lift
   MP1K_R,    //18 movable long pinion lock rotate
   MP2_L,     //19 movable long pinion lift
   MP2K_R,    //20 movable long pinion lock rotate
   MP3_L,     //21 movable long pinion lift
   MP3K_R,    //22 movable long pinion lock rotate
   P11_L,     //23 movable long pinion left connector lift
   P21_L,     //24 movable long pinion left connector lift
   P31_L,     //25 movable long pinion left connector lift
   P12_L,     //26 fixed long pinion left connector lift
   P22_L,     //27 fixed long pinion left connector lift
   P32_L,     //28 fixed long pinion left connector lift
   P13_L,     //29 movable long pinion right connector lift
   P23_L,     //30 movable long pinion right connector lift
   P14_L,     //31 fixed long pinion right connector lift
   P24_L,     //32 fixed long pinion right connector lift
   FP1K_R,    //33 fixed long pinion lock rotate
   FP2K_R,    //34 fixed long pinion lock rotate
   FP3K_R,    //35 fixed long pinion lock rotate
   RP1_L,     //36 rack pinion lift
   RP2_L,     //37 rack pinion lift
   RP3_L,     //38 rack pinion lift
   CL2_R,     //39 carry lifter rotate
   CS2_R,     //40 carry sector rotate
   CW2_L,     //41 carry warning arms lift
   CW2_R,     //42 carry warning arms rotate (for reset)
   CSK2_R,    //43 carry sector keepers rotate
   CSK2_L,    //44 carry sector keepers lift
   CL3_R,     //45 carry lifter rotate
   CS3_R,     //46 carry sector rotate
   CW3_L,     //47 carry warning arms lift
   CW3_R,     //48 carry warning arms rotate (for reset)
   CSK3_R,    //49 carry sector keepers rotate
   CSK3_L,    //50 carry sector keepers lift
   S1_L,      //51 Store column lift
   S1_R,      //52 Store column rotate
   S2_L,      //53 Store column lift
   S2_R,      //54 Store column rotate
   S3_L,      //55 Store column lift
   S3_R,      //56 Store column rotate
   S4_L,      //57 Store column lift
   S4_R,      //58 Store column rotate
   S5_L,      //59 Store column lift
   S5_R,      //60 Store column rotate
   S6_L,      //61 Store column lift
   S6_R,      //62 Store column rotate
   RR_L,      //63 rack restorer lift
   RR_R,      //64 rack restorer rotate
   SIGN_R,    //65 sign wheel rotate
   SIGN_L,    //66 sign wheel lift
   CTR1_R,    //67 counter 1 rotate
   CTR1_L,    //68 counter 1 lift
   CTR2_R,    //69 counter 2 rotate
   CTR2_L,    //70 counter 2 lift
   RK_L,      //71 rack lock lift
   TEST_R,    //72 a motor test driver
   NUM_MOTORS //73
};

#define NM 99      //TEMP

//input signals multiplexed into SWITCH_INPUT according to MUXA/B/C/D
#define SW_A1       // index position for Mill digit wheel
#define SW_A2 0     // index position for Mill digit wheel
#define SW_A3       // index position for Mill digit wheel
#define SW_F2 3     // index position for carriage 2
#define SW_F3       // index position for carriage 3
#define SW_SIGN     // sign wheel odd/even
#define SW_CTR1     // counter 1 is zero
#define SW_CTR2     // counter 2 is zero
#define SW_S1  1     // index position for store wheel
#define SW_S2       // index position for store wheel
#define SW_S3       // index position for store wheel
#define SW_S4       // index position for store wheel
#define SW_S5       // index position for store wheel
#define SW_S6       // index position for store wheel *** RAN OUT OF SWITCHES!
#define SW_RR  2     // index position for rack restorer
#define F2_RUNUP    // carriage runup
#define F3_RUNUP    // carriage runup

enum movement_t { ROTATE, LIFT, ANY_MOVEMENT };  // movement types
enum motor_state_t { ON, OFF };

struct motord_t { //**** a motor descriptor
   int motor_number;                     // 0..95, as defined symbolically above
   enum movement_t motor_type;           // does it rotate or lift by default?
   const char* axle_name;                // name used in the "rot" or "lift" commands
   const char* axle_descr;               // more verbose description
   int gear_big, gear_small;             // if not zero, gear reduction tooth counts
   int compensating_lifter;              // the lift motor we should counter-rotate when this motor is rotated
   bool assigned;                        // has this motor been assigned a controller?
   int board_number;                     // what board number? (1..6)
   int board_position;                   // what position (1..16) on the board?
   bool always_on;                       // should this motor be always enabled, ie powered on?
   bool full_steps;                      // should we round movements down to full steps so we can power down between movements?
   bool temp_on;                         // is this motor temporarily held on?
   enum motor_state_t motor_state;       // is this motor currently on or off?
   int microstep_offset;                 // current CW offset from a full-step position, 0..uSTEPS_PER_STEP-1
   int deficit;                          // the numerator of the current fractional ustep deficit; for denominator see queue_movement()
   bool move_queued, moving_now;         // is this motor scheduled for movement, and is it moving now?
   bool clockwise;                       // in which direction?
   int usteps_needed;                    // how many movement steps are needed for all time units
   int usteps_done;                      // how many steps have been done in the current time unit
   int ending_ustep;                     // ending step number in the current time unit
   unsigned long start_time;             // starting time for steps
   unsigned step_delta_time;             // time between steps
   unsigned long last_ustep_time_usec;   // when the last step was done
   unsigned start_pct, end_pct;          // start and end of movement in the time unit, from 0..99
   int current_position;                 // current position relative to neutral, in units that depend on the axle
};

struct fct_move_t {         // basic movement specification
   const char* keyword;     // keywords, the first often identifying the axle to move
   int motor_num;           // the motor to move
   int position;            // where it should move to (positive: up or clockwise)
   bool distance_given; }; // or, if this is true, the distance it should move
#define MOVE_DISTANCE true
#define NOMOVE INT_MAX

struct script_t {
   const char* name;             // the name of the script
   //   const char (*commands)[];
   const char** commands;        // const pointer to an array of compound commands
   //   const char **next_command;    // pointer to where in the array to execute next  NO: can't do one script multiple times
   //   struct script_t *next_script; // pointer to the next script being simultaneously executed NO: can't do one script multiple times
};

extern struct config_t {  // the configuration record written to non-volatile EEPROM memory
#define CONFIG_ID "Babbage"
   char id[8];
   struct { // the calibration values for figure wheel stacks
      bool unused;
      int degrees; } finger_zero_degrees[NUM_MOTORS]; // valid for A,F,S,RR rotators only. -1 if not set
} config;

extern script_t named_scripts[], * divide_restore_copy[];
extern struct motord_t motor_descriptors[];
extern struct motord_t* motor_num_to_descr[];
extern char cmdline[CMDLENGTH];
extern const char* help[];
extern int debug, motors_queued, cyclenum;
extern bool got_error, script_step;
extern unsigned long timeunit_usec;
extern struct fct_move_t fct_zero[], fct_weaklock[];

void assert(bool test, const char* msg);
void assert(bool test, const char* msg1, const char* msg2);
void assert(bool test, const char* msg, int value);
void execute_commands(const char* ptr);
void flush_input(void);
int wait_for_char(void);
void error(const char* msg, const char* info);
bool scan_key(const char** pptr, const char* keyword);
bool scan_int(const char** pptr, int* pnum, int min, int max);
struct motord_t* scan_axlename(const char** pptr, enum movement_t which, bool showerr);
void initialize_iopins(void);
void initialize_motors(void);
void getstring(char* buf, unsigned buflen);
void queue_movement(struct motord_t* pmd, enum movement_t movetype, int distance, int start = 0, int end = 99);
bool do_movements(unsigned long duration_usec);
void clear_movements(void);
void show_motors(void);
bool do_step_wait(void);
void do_homescript(void);
struct fct_move_t* do_function(struct fct_move_t* move, const char** pptr);
void do_calibrate(const char** pptr);
void read_config(void);
void write_config(void);
int read_switch(int switch_number);
void do_test(void);

void power_motor(struct motord_t *pmd, enum motor_state_t onoff, bool forceoff = false);
void power_motors(enum motor_state_t onoff, bool all = false);

//*
