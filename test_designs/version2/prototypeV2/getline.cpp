#include "prototype.h"

/***** input line editor

    Supports saved commanda retrieved with up-arrow and down-arrow,
    and interline editing using left-right arrows, backspace, and DEL.

    This is designed for an xterm-like terminal emulator, eg PuTTY.

    We assume that it generates these characters from keyboard input:
      ESC [ A-D    for the arrow keys
      ESC [ 1 ~    for the HOME key
      ESC [ 2 ~    for the INS key
      ESC [ 3 ~    for the DEL key
      ESC [ 4 ~    for the END key
      ESC [ 1 1 ~  for the F1 key
      ESC [ 1 2 ~  for the F2 key
      0x0d         for the Enter key

   We assume that it handles output to the screen as follows:
      0x08         is non-destructive cursor-left
      ESC [ C      is non-destructive cursor-right
      0x0d         is non-destructive move cursor to left margin
      0x0a         is non-destructive move cursor down one line
*/

#define MAX_SAVED_CMDS 20
#define CURSORRIGHT "\e[C"

char savedcmds[MAX_SAVED_CMDS][CMDLENGTH];
int oldest_cmd = 0, newest_cmd = 0, current_cmd, n_saved_cmds = 0;

int curchr, nulchr; // character indices to the current and ending NUL characters in the buffer

static int nextchar(void) { // get a character following soon
   delay(3);  // only wait 3 milliseconds
   if (Serial.available()) return Serial.read();
   return 0; }

int getcharacter(void) { // get a character and translate some special sequences to single characters
   while (Serial.available() == 0);  // wait for a character
   int ch = Serial.read();
   if (ch == ESC) {
      if (nextchar() == '[') {
         ch = nextchar(); // what follows the left bracket
         if (ch == 'A') return UPARROW;     // ESC [ A
         if (ch == 'B') return DOWNARROW;   // ESC [ B
         if (ch == 'C') return RIGHTARROW;  // ESC [ C
         if (ch == 'D') return LEFTARROW;   // ESC [ D
         if (ch == '2' && nextchar() == '~') return INSERT;  // ESC [ 2 ~
         if (ch == '3' && nextchar() == '~') return DEL;  // ESC [ 3 ~
         if (ch == '4' && nextchar() == '~') return END;  // ESC [ 4 ~
         if (ch == '1') {  // ESC [ 1
            ch = nextchar(); // what follows ESC [ 1
            if (ch == '~')  return HOME;  // ESC [ 1 ~
            if (ch == '1' && nextchar() == '~') return F1; // ESC [ 1 1 ~
            else if (ch == '2' && nextchar() == '~') return F2; } // ESC [ 1 2 ~
         return '?'; } // unsupported escape sequence
      return ESC; } // naked escape
   return ch; }  // all other characters

static void reprint_line(int cursor) {
   Serial.printf("\r>%s \r" CURSORRIGHT, cmdline);  // extra blank in case erasing an old char
   while (cursor--) Serial.print(CURSORRIGHT); } // reposition the cursor

static void use_stored_line(void) {
   strlcpy(cmdline, savedcmds[current_cmd], sizeof(cmdline)); // grab the stored line
   Serial.print("\r "); while (nulchr--) Serial.print(' '); // blank out the displayed line
   Serial.printf("\r>%s", cmdline); // write the new line
   curchr = nulchr = strlen(cmdline); } // start the cursor at the end

void getcmdline() {  // get a command from the keyboard into cmdline
   current_cmd = -1;  // no current command in the list of saved commands
   curchr = nulchr = 0; // index of current (cursor to the left of) and ending NUL chars
   flush_input();
   Serial.print('>');
   char ch;
   while (true) {
      ch = getcharacter();
      if (ch == ENTER) {
         // Enhancement 1: Enter on blank line repeats newest command
         if (nulchr == 0 && n_saved_cmds > 0) {
            strlcpy(cmdline, savedcmds[newest_cmd], sizeof(cmdline));
            Serial.print(cmdline); // Show the command being repeated
            nulchr = strlen(cmdline); }
         break; } // command is complete
      else if (ch == HOME) {
          curchr = 0;  Serial.print("\r" CURSORRIGHT); }
      else if (ch == END) {
          while (curchr < nulchr) {
            ++curchr; Serial.print(CURSORRIGHT); } }
      else if (ch == DEL) {
         if (curchr < nulchr) { // not at the right end 
            if (curchr < nulchr - 1) { // if not deleting the last char
               for (int src = curchr + 1; src < nulchr; ++src)
                  cmdline[src - 1] = cmdline[src]; // shift chars left
               cmdline[--nulchr] = 0; // retract the nul
               reprint_line(curchr); }
            else { // deleting the last char
               Serial.print(" \b"); // just erase last char
               --nulchr; } } }
      else if (ch == BACKSPACE) {      // backspace:
         if (curchr > 0) {
            if (curchr < nulchr) { // if not deleting the last char
               for (int src = curchr; src < nulchr - 1; ++src)
                  cmdline[src - 1] = cmdline[src]; // shift chars left
               cmdline[--nulchr] = 0; // retract the nul
               reprint_line(--curchr); }
            else { // removing the last character
               Serial.print("\b \b"); // just erase last char
               --curchr; --nulchr; } }  
         else {
            if (nulchr == 0 && n_saved_cmds > 1) { // backspace if empty reverses last two commands
               int prev_cmd = newest_cmd - 1;
               if (prev_cmd < 0) prev_cmd = MAX_SAVED_CMDS - 1;
               char temp[CMDLENGTH];  // Reverse the last two commands in history
               strlcpy(temp, savedcmds[newest_cmd], sizeof(temp));
               strlcpy(savedcmds[newest_cmd], savedcmds[prev_cmd], sizeof(savedcmds[newest_cmd]));
               strlcpy(savedcmds[prev_cmd], temp, sizeof(savedcmds[prev_cmd]));
               // Repeat the command that is now at the "newest" position (the old next-to-newest)
               strlcpy(cmdline, savedcmds[newest_cmd], sizeof(cmdline));
               Serial.print(cmdline);
               nulchr = strlen(cmdline);
               break; } } }  
      else if (ch == ESC) { // escape: start over on a fresh screen line
         Serial.println();
         cmdline[0] = curchr = nulchr = 0;
         return; }
      else if (ch == UPARROW) { // up arrow: recall older stored command
         if (n_saved_cmds > 0) {
            if (current_cmd < 0) // never used the newest
               current_cmd  = newest_cmd; // so use it
            else { // go to an older one
               if (current_cmd != oldest_cmd) if (--current_cmd < 0) current_cmd = MAX_SAVED_CMDS - 1; }
            use_stored_line(); } }
      else if (ch == DOWNARROW) { // down arrow: recall newer stored command
         if (n_saved_cmds > 0) {
            if (current_cmd >= 0) { // go to a newer one
               if (current_cmd != newest_cmd) if (++current_cmd >= MAX_SAVED_CMDS) current_cmd = 0;
               use_stored_line(); } } }
      else if (ch == LEFTARROW) {
         if (curchr > 0) {
            Serial.print(BACKSPACE);
            --curchr; } }
      else if (ch == RIGHTARROW) {
         if (curchr < nulchr) {
            Serial.print(CURSORRIGHT);
            ++curchr; } }
      else if (ch == F1) { // debug hack: F1 dumps command table
         Serial.printf("n_saved_cmds %d, current_cmd %d, newest_cmd %d, oldest_cmd %d, MAX_SAVED_CMDS %d\n",
                       n_saved_cmds, current_cmd, newest_cmd, oldest_cmd, MAX_SAVED_CMDS);
         int slot = oldest_cmd;
         for (int i = 0; i < n_saved_cmds; ++i) {
            Serial.printf("slot %d: %s\n", slot, savedcmds[slot]);
            if (++slot >= MAX_SAVED_CMDS) slot = 0; } }
      else if (ch == F2) { // debug hack: F2 dumps character pointers
         Serial.printf("\ncurchr %d, nulchr %d, sizeof(cmdline) %d\n",
                       curchr, nulchr, sizeof(cmdline)); }
      else if (isprint(ch)) { // insert a normal character
         if (nulchr < (int)sizeof(cmdline) - 2) { // if there's room in the buffer
            if (curchr < nulchr) { // we're not adding to the end
               for (int src = nulchr - 1; src >= curchr; --src)
                  cmdline[src + 1] = cmdline[src]; // so shift chars after us right
               cmdline[++nulchr] = 0; // advance the nul
               cmdline[curchr++] = ch; // insert the character
               reprint_line(curchr); } // reprint the line
            else { // adding to the end: just print it
               Serial.print(ch); 
               cmdline[curchr++] = ch;
               nulchr = curchr; } } } }
   
   Serial.println(); // move to the start of the next line on the screen
   cmdline[nulchr] = 0;
   if (nulchr > 0) { // if the command isn't null, save it , if not the same as the most recent
      if (n_saved_cmds > 0) { // if there is at least one other saved command
         if (strcmp(cmdline, savedcmds[newest_cmd]) != 0) {
            if (++newest_cmd >= MAX_SAVED_CMDS) newest_cmd = 0; // make a new slot to save the command
            if (newest_cmd == oldest_cmd) { // buffer full: remove oldest command
                if (++oldest_cmd >= MAX_SAVED_CMDS) oldest_cmd = 0; }
            else ++n_saved_cmds; 
            strlcpy(savedcmds[newest_cmd], cmdline, sizeof(cmdline));
         } }
      else {
         n_saved_cmds = 1; // add the first command
         strlcpy(savedcmds[newest_cmd], cmdline, sizeof(cmdline));  } } }
