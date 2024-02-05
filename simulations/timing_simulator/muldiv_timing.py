#
# A program to compute and graph AE multiplication and division timing
# using various algorithms and test programs
#
# L. Shustek, 17 Sept 2023 and later
# L. Shustek, 30 Sept 2023
#   change to using Matplotlib to create graphs instead of exporting CSV files to Excel
# L. Shustek, 6 Dec 2023
#   add 3D stacked column chart for different operand lengths
# L. Shustek, 14 Dec 2023
#   add the Lovelace calculation of Bernoullli B7 
#   implement implied decimal point
#   implement signed multiplication and division

def do_multiply(multiplicand, multiplier, use_table=True):
    setup_cycles = 0
    sign = 1
    if multiplicand < 0:
        multiplicand = -multiplicand
        sign = -1
        setup_cycles += 1
    if multiplier < 0:
        multiplier = -multiplier
        sign *= -1
        setup_cycles += 1
    if multiplicand < multiplier: #make multiplier smaller
        multiplicand, multiplier = multiplier, multiplicand #how does the engine do this?
    multiplier_size = len(str(multiplier))
    if use_table: setup_cycles += 1+9 #number of cycles to create the table
    else: setup_cycles += 1
    product = 0
    multiply_cycles = 0 #cycles for the multiplication proper, without setup
    for loop in range(multiplier_size):
        next_digit = multiplier % 10
        multiply_cycles += 1 #one cycle for choosing the table entry, testing for zero, and shifting
        if next_digit > 0: #skip zero multiplier digits
            product += next_digit*multiplicand * 10**loop 
            if use_table:
                multiply_cycles += 1 #cycles for adding the single table entry
            else:
                multiply_cycles += 1*next_digit #cycles for adding the multiplicand next_digit times
        else: multiply_cycles += 1 #even zero takes two cycles
        multiplier //= 10
    product = sign * (product // 10**decimals) #need to do this incrementally, at no cycle cost
    return {"product":product, "total_cycles":setup_cycles + multiply_cycles, "digit_cycles":multiply_cycles/(multiplier_size)}

def do_divide(dividend, divisor, use_table=True, selector_digits=2):
    if divisor == 0:
        return {"quotient":0, "remainder":0, "total_cycles":0, "digit_cycles":0}
    sign = 1
    if dividend < 0:
        dividend = -dividend
        sign = -1
    if divisor < 0:
        divisor = -divisor
        sign *= -1
    #if dividend < divisor:  #not correct when decimals>0
    #    return {"quotient":0, "remainder":dividend, "total_cycles":2, "digit_cycles":0}
    #shift the divisor left so it lines up with the dividend
    divisor_size = len(str(divisor)) + 1 #include leading 0
    dividend_size = len(str(dividend)) + 1 # include leading 0
    shift_distance = dividend_size - divisor_size
    setup_cycles = 2 + shift_distance  #1 cycle per shift plus overhead to determine sizes?
    if use_table: setup_cycles += 9  #cycles to make the table (no overlap with shifts?)
    quotient = 0 #get ready to do the division
    divide_cycles = 0 #cycles for the division proper, without setup
    #the number of positions for trial subtractions is one more than the difference 
    #between the number of significant digits in the dividend and the divisor
    for loop in range(shift_distance+1+decimals):
        quotient *= 10
        if use_table:
            dividend_topn = dividend // (10**(dividend_size-selector_digits)) #top n digits of the current dividend
            if dividend_topn >= 10**selector_digits: print(f"ERROR: dividend topn too big for {selector_digits} digits: {dividend_topn}")
            divide_cycles += 1 #one cycle for selecting the table axis?
            for multiple_number in range(1,10): #find the multiple whose top n digits are no larger than the dividend's
                trial_multiple = divisor * multiple_number 
                trial_multiple_topn = trial_multiple // 10**(divisor_size-selector_digits)
                if trial_multiple_topn > dividend_topn: 
                    if multiple_number > 1: multiple_number -= 1 #always at least subtract the first table entry
                    break;
            multiple = divisor * multiple_number * 10**(shift_distance-loop)
            dividend -= multiple #subtract the chosen multiple
            quotient += multiple_number #increment the quotient
            divide_cycles += 1 #cycles to subtract chosen table axis
        else: #no table: repeated subtraction until underflow
            while (dividend > 0):
                dividend -= divisor * 10**(shift_distance-loop)
                quotient += 1
                divide_cycles += 1 #cycles for each subtraction
        while dividend < 0: #we subtracted too much
            # This happens at most once with no table, or for 2-digit table selection when the 2 digits match.
            # It could happen more than once for 1-digit table selection.
            dividend += divisor * 10**(shift_distance-loop) #add back the divisor
            quotient -= 1
            divide_cycles += 1 #cycles for each correction cycle
        #step down the divisor and all the table axes
        dividend_size -= 1
        if not use_table: divide_cycles += 1 #time for shift
        #shifting takes no time when using a table because it can be overlapped with selection?
    return {"quotient":quotient, "remainder":dividend*sign, "total_cycles":setup_cycles + divide_cycles, 
            "digit_cycles":divide_cycles/(shift_distance+1+decimals)}

def divide(dividend, divisor, show=False, use_table=True, selector_digits=2):
    answer = do_divide(dividend, divisor, use_table, selector_digits)
    wrong = answer["quotient"]*divisor + answer["remainder"] != dividend \
        or answer["remainder"] > divisor or answer["remainder"] < 0
    if wrong: print ("WRONG ANSWER:")
    if wrong or show: 
       print(f'{dividend} / {divisor} = {answer["quotient"]} remainder {answer["remainder"]}'
             f' in {answer["total_cycles"]} time units and {answer["digit_cycles"]:.2f} per digit')
    return answer

def multiply(multiplicand, multiplier, show=False, use_table=True):
    answer = do_multiply(multiplicand, multiplier, use_table)
    wrong = answer["product"] != multiplicand * multiplier
    if wrong: print ("WRONG ANSWER:")
    if wrong or show: 
       print(f'{multiplicand} * {multiplier} = {answer["product"]}'
             f' in {answer["total_cycles"]} time units and {answer["digit_cycles"]:.2f} per digit')
    return answer

def decimal(n): #stringify a number that has an implied decimal point
    if n<0: 
        n=-n
        negative=True
    else: negative=False
    return f'{"-" if negative else ""}{n//10**decimals:1d}.{n%10**decimals:0{decimals}d}'

def highest_proper_factor(number, max_tests=9999999999):
    trial = (number+1) // 2
    tests = 0
    cycles = 0
    while trial > 1:
        answer = divide(number, trial, use_table=False)
        cycles += answer["total_cycles"]
        if answer["remainder"] == 0: break;
        tests += 1
        if tests > max_tests: break;
        trial -= 1
    return {"factor":trial, "minutes":cycles*minutes_per_cycle, "tests":(number+1)//2+1-trial}

class stats: #averaged statistics for one datapoint in the design space
    def __init__(self):
        self.sum, self.num, self.max = 0, 0, 0
        self.min = 9999
    def accum(self, value):
        self.sum += value
        if value > self.max: self.max = value
        if value < self.min: self.min = value
        self.num += 1
    def print(self, scale=1.0): #output avg and negative/positive error bar limits
        #to plot in Excel: click series, Chart Design, Add Chart Element, Error Bars, more error bar options
        #      "Format Error Bars", barchart icon, "Error Amount", "Custom", "Specify Value", select range
        avg = self.sum / self.num if self.num > 0 else 0
        print(f"{avg*scale:13.2f}, {self.min*scale:8.2f}, {self.max*scale:8.2f}, ", end="")

import matplotlib.pyplot as plt
import numpy as np
import random
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import LightSource

seconds_per_unit = .157
units_per_cycle = 20
minutes_per_cycle = seconds_per_unit * units_per_cycle / 60.
decimals = 8 #digits to the right of the decimal point

def rand(ndigit): #generate an ndigit number
    return random.randint(10**(ndigit-1), 10**ndigit-1)

class graphline: #a single line to be added to a Matplotplib graph
    def __init__(self, name, scale=1.0):
        self.name = name
        header = name if scale!=1.0 else name+"/dg"
        print(f"{header:32.32s},,,", end="")
        self.scale = scale
        self.datastats = [] #list of statistics for the design points
        self.numstats = 0
        self.x = [] #list of x coordinates
        self.y = [] #list of y coordinates
        self.err = [[],[]] #negative, then positive error bar distances
    def newpoint(self): #start a new design point statistic
        self.datastats.append(stats())
        self.numstats += 1
    def updatepoint(self, value): #accumulate the value of that point
        self.datastats[self.numstats-1].accum(value)
    def closepoint(self, ndigits): #add the completed point to the graph line data
        stat=self.datastats[self.numstats-1] #the most recently added point's statistics
        self.x.append(ndigits)
        avg = stat.sum/stat.num if stat.num > 0 else 0
        self.y.append(avg*self.scale)
        self.err[0].append((avg-stat.min)*self.scale) #negative error bar distance
        self.err[1].append((stat.max-avg)*self.scale) #positive error bar distance
        stat.print(scale=self.scale)
    def addline(self, plot): #plot all the points with error bars, and a line through them
        plot.errorbar(self.x, self.y, self.err, fmt='.', markersize=3, linestyle='-', linewidth=.75, elinewidth=.75, capsize=2, label=self.name)
       
if False: #debugging with specific cases
    divide(12345,150, show=True)
    divide(12345,111, show=True)
    multiply(54211139001182356394, 142957977320214560, show=True)
    multiply(1234,34, show=True)
    divide(63526681474527201380, 8832, show=True)
    divide(14033, 10, show=True) #axis 9 for digit 1
    divide(378, 95 , show=True) #axis 1 for digit 1
    divide(123456789, 77, show=True)
    exit()

if False: #more special tests of possible demo programs
    max_tests = 20
    good_ones = 0
    while(good_ones < 20):
        number = rand(4)
        answer = highest_proper_factor(number, max_tests=max_tests)
        if answer["tests"] > 1 and answer["tests"] <= max_tests:
            good_ones += 1
            print(f'highest factor of {number} is {answer["factor"]} in {answer["minutes"]:.1f} minutes after {answer["tests"]} tests')
    exit()
    number = 1
    for loop in range(2,10):
        number = number * 10 + loop
        highest_proper_factor(number)
    exit()

#-------------------------------------------------------------------------------------------------------
# Create 3D column charts of average multiplication and division times
# for random numbers with various combinations of operand lengths,
# both with and without using a precomputed table of multiples.
#-------------------------------------------------------------------------------------------------------
if False: 
    ntests=1000 # how many random tests to do for each combination of operand lengths

    def graph3D(multiplication): #do a 3D graph for either operation
        fig = plt.figure(dpi=300, clip_on=True)
        ax = fig.add_subplot(111, projection = "3d")
        ax.set_title(("multiplication" if multiplication else "division") + " by random numbers", fontsize="x-large")
        ax.set_xlabel(("multiplicand" if multiplication else "dividend") + " length")
        ax.set_ylabel(("multiplier" if multiplication else "divisor") + " length") 
        ax.set_zlabel("minutes")
        ax.set_xlim3d(17,0)
        if multiplication: ax.set_ylim3d(0,18) #get tall columns in the back left corner
        else: ax.set_ylim3d(17,0) #to avoid obscuring short ones
        ax.set_xticks([1,5,10,15])
        ax.set_yticks([1,5,10,15])
        
        xpos = [1,5,10,15,1,5,10,15,1,5,10,15,1,5,10,15 ] #center positions of columns
        ypos = [1,1,1,1,5,5,5,5,10,10,10,10,15,15,15,15 ] 
        xpos = [*xpos, *xpos]; #repeat for both table and no-table versions
        ypos = [*ypos, *ypos];
        zpos = np.zeros(32) #base of the columns
        dx = np.full(32,1) #width of columns
        dy = np.full(32,1) #depth of columns
        dz = np.zeros(32) #will become the height of the columns

        for ndx in range(32): #16 combinations with table, then 16 without
            tablepoint = stats()
            for testnum in range(ntests):
                operand1 = rand(xpos[ndx])
                operand2 = rand(ypos[ndx])
                if multiplication:
                    answer = multiply(operand1, operand2, use_table=ndx>=16)
                else: answer = divide(operand1, operand2, use_table=ndx>=16, selector_digits=2)
                tablepoint.accum(answer["total_cycles"]*minutes_per_cycle) #accumulate the minutes
            dz[ndx] = tablepoint.sum/tablepoint.num

        if multiplication: #why the hell do we need to do this??
            for i in range(32): ypos[i] = ypos[i]-1
        for i in range(16): xpos[i] = xpos[i]-1.0 #offset the columns to not overlap
        for i in range(16,32): xpos[i] = xpos[i]+0.0 #but be adjacent
        colors = ['y', 'r']
        barcolors = [*(colors[0]*16), *(colors[1]*16)] #no table, then table
        light=LightSource(azdeg=120 if multiplication else 360-315);
        ax.bar3d(xpos, ypos, zpos, dx, dy, dz, barcolors, shade=True, lightsource=light) #draw all the columns
        color1_proxy = plt.Rectangle((0, 0), 1, 1, fc=colors[0]) #some magic to create the legend
        color2_proxy = plt.Rectangle((0, 0), 1, 1, fc=colors[1])
        ax.legend([color1_proxy, color2_proxy], ['no table', 'table'], bbox_to_anchor=(1.2, 1.0), loc='upper right', frameon=False)
        plt.savefig("multiplication.jpg" if multiplication else "division.jpg", bbox_inches="tight")
        print("done")
        #plt.show()

    graph3D(True) # multiplication
    graph3D(False) # division
    # ****** multiplication ******

    exit()

#-------------------------------------------------------------------------------------------------------
# Simulate the computation of Bernoulli number B7 as shown in Note G of Ada Lovelace's translation
# of Luigi Menabrea's 
#-------------------------------------------------------------------------------------------------------
if True: # see https://twobithistory.org/2018/08/18/ada-lovelace-note-g.html
    if False: #miscellaneous spot tests
        multiply(1234567,123456, show=True, use_table=False)
        multiply(1234567,123456, show=True, use_table=True)
        divide(1234567,12345, show=True, use_table=False)
        divide(1234567,12345, show=True, use_table=True)
        print(decimal(0))
        print(decimal(1))
        print(decimal(1234))
        print(decimal(12345))
        print(decimal(123456))
        print(decimal(1234567))
        print(decimal(1000000))
    print()

#*** compute B7 using modern arithmetic expressions
    B1=1/6
    B3=-1/30
    B5=1/42
    n=4
    B7=-(1/2)*((2*n-1)/(2*n+1))
    B7 += B1*(2*n/2)
    B7 += B3*((2*n*(2*n-1)*(2*n-2))/(2*3*4))
    B7 += B5*((2*n*(2*n-1)*(2*n-2)*(2*n-3)*(2*n-4))/(2*3*4*5*6))
    print("B7:", B7)

#*** compute B5 using modern arithmetic expressions
    B1=1/6
    B3=-1/30
    n=3
    B5=-(1/2)*((2*n-1)/(2*n+1))
    B5 += B1*(2*n/2)
    B5 += B3*((2*n*(2*n-1)*(2*n-2))/(2*3*4))
    print("B5:", B5)

#*** compute B5 using modern arithmetic expressions, optimized
    B1=1/6
    B3=-1/30
    n=3
    B5=-(1/2)*((2*n-1)/(2*n+1))
    B5 += B1*n
    B5 += B3*((n*(2*n-1)*(2*n-2))/(3*4))
    print("B5 opt:", B5)

#***compute B7 using Lovelace's instruction sequences, with floating-point numbers
#initial engine conditions
    v1=1              #constant 1
    v2=2              #constant 2
    v3=4              #n=4, to compute the 4th number, B(2n-1), or B7
    v4=v5=v6=v7=v8=v9=v10=v11=v12=v13=0 
                      #uninitialized variables in the store are zero
    v21=1/6           #B1  previously computed values
    v22=-1/30         #B3
    v23=1/42          #B5
    v24=0             #B4 will be accumulated here
#program: computes B7 = -A0 - A1B1 - A3B3 - A5B5
    v4=v5=v6 = v2*v3  #step 1: 2n
    v4 = v4-v1        #step 2: 2n-1
    v5 = v5+v1        #step 3: 2n+1
    v11 = v4/v5       #step 4: (2n-1)/(2n+1)
    v11 = v11/v2      #step 5: (1/2)((2n-1)/(2n+1))
    v13 = v13-v11     #step 6: -(1/2)((2n-1)/(2n+1)) = A0
    v10 = v3-v1       #step 7: n-1  counter=3
    v7 = v2+v7        #step 8: 2    copy constant
    v11 = v6/v7       #step 9: 2n/2 = A1
    v12 = v21*v11     #step 10: A1*B1
    v13 = v12+v13     #step 11: A0+A1*B1
    v10 = v10-v1      #step 12: n-2  counter=2
    v6 = v6-v1        #step 13: 2n-1
    v7 = v1+v7        #step 14: 2+1 = 3
    v8 = v6/v7        #step 15: (2n-1)/3
    v11 = v8*v11      #step 16: (2n/2)*((2n-1)/3)
    v6 = v6-v1        #step 17: 2n-2
    v7 = v1+v7        #step 18: 3+1 = 4
    v9 = v6/v7        #step 19: (2n-2)/4
    v11 = v9*v11      #step 20: (2n/2)*((2n-1)/3)*((2n-2)/4) = A3
    v12 = v22*v11     #step 21: A3*B3
    v13 = v12+v13     #step 22: A0+A1*B1+A3*B3
    v10 = v10-v1      #step 23: n-3   counter = 1
    v6 = v6-v1        #step 13: 2n-3
    v7 = v1+v7        #step 14: 4+1 = 5
    v8 = v6/v7        #step 15: (2n-3)/5
    v11 = v8*v11      #step 16: (2n/2)*((2n-1)/3)*((2n-2)/4) *((2n-3)/5)
    v6 = v6-v1        #step 17: 2n-4
    v7 = v1+v7        #step 18: 5+1 = 6
    v9 = v6/v7        #step 19: (2n-4)/6
    v11 = v9*v11      #step 20: (2n/2)*((2n-1)/3)*((2n-2)/4)*((2n-3)/5)*(2n-4)/6)= A5
    v12 = v23*v11     #step 21: A5*B5
    v13 = v12+v13     #step 22: A0+A1*B1+A3*B3+A4*B5
    v10 = v10-v1      #step 23: n-4   counter = 0
    v24 = v13+v24     #step 24: A0+A1*B1+A3*B3+A5*B5 = B7
    v3 = v1+v3        #step 25: n=5  ready to compute B9
    print("B7: ", v24)

    ADD, SUB, MUL, DIV = 0, 1, 2, 3
    def oper(x,op,y):
        global cum_cycles
        if op == ADD: 
            result = x+y
            cum_cycles += 1
        if op == SUB: 
            result = x-y
            cum_cycles += 1
        if op == MUL: 
            answer = do_multiply(x, y, use_table=tables)
            result = int(answer["product"])
            cum_cycles += answer["total_cycles"]
        if op == DIV: 
            answer = do_divide(x, y, use_table=tables)
            result = int(answer["quotient"])
            cum_cycles += answer["total_cycles"]
        #print(decimal(result))
        return result
    def Bresult(number, answer):
        print(f'{number} is {decimal(answer)} using {decimals} decimals {"with" if tables else "without"} tables in {cum_cycles*minutes_per_cycle:.1f} minutes')

#-------------------------------------------------------------------------------------------------------
# graph the time it takes to simulate exactly the Lovelace calculation of B7
# with and without tables, and for a variety of digits to the right of the decimal point
#-------------------------------------------------------------------------------------------------------
    numdecimals = [3, 4, 6, 8]
    times = np.zeros((2, len(numdecimals)))
    for tables in [True, False]: #with and without tables
        for numdec in range(len(numdecimals)): #for the different number of decimals
            decimals = numdecimals[numdec]
        #*** compute B7 using Lovelace's instruction sequences, with calls to our simulator
            cum_cycles = 0
        #initial engine conditions
            v1=1 * 10**decimals            #constant 1
            v2=2 * 10**decimals            #constant 2
            v3=4 * 10**decimals            #n=4, to compute the 4th number, B(2n-1), or B7
            v4=v5=v6=v7=v8=v10=v11=v12=v13=0 
                                        #uninitialized variables in the store are zero
            v21=int(1/6 * 10**decimals)    #B1  previously computed Bernoulli numbers
            v22=-int(1/30 * 10**decimals)  #B3
            v23=int(1/42 * 10**decimals)   #B5
            v24=0                          #B7 will be put here
        #program: computes B7 = -A0 - A1B1 - A3B3 - A5B5
            v4=v5=v6 = oper(v2,MUL,v3)  #step 1: 2n
            v4 = oper(v4,SUB,v1)        #step 2: 2n-1
            v5 = oper(v5,ADD,v1)        #step 3: 2n+1
            v11 = oper(v4,DIV,v5)       #step 4: (2n-1)/(2n+1)
            v11 = oper(v11,DIV,v2)      #step 5: (1/2)((2n-1)/(2n+1))
            v13 = oper(v13,SUB,v11)     #step 6: -(1/2)((2n-1)/(2n+1)) = A0
            v10 = oper(v3,SUB,v1)       #step 7: n-1  counter=3
            v7 = oper(v2,ADD,v7)        #step 8: 2    copy constant
            v11 = oper(v6,DIV,v7)       #step 9: 2n/2 = A1
            v12 = oper(v21,MUL,v11)     #step 10: A1*B1
            v13 = oper(v12,ADD,v13)     #step 11: A0+A1*B1
            v10 = oper(v10,SUB,v1)      #step 12: n-2  counter=2
            v6 = oper(v6,SUB,v1)        #step 13: 2n-1
            v7 = oper(v1,ADD,v7)        #step 14: 2+1 = 3
            v8 = oper(v6,DIV,v7)        #step 15: (2n-1)/3
            v11 = oper(v8,MUL,v11)      #step 16: (2n/2)*((2n-1)/3)
            v6 = oper(v6,SUB,v1)        #step 17: 2n-2
            v7 = oper(v1,ADD,v7)        #step 18: 3+1 = 4
            v9 = oper(v6,DIV,v7)        #step 19: (2n-2)/4
            v11 = oper(v9,MUL,v11)      #step 20: (2n-2)*((2n-1)/3)*((2n-2)/4) = A3
            v12 = oper(v22,MUL,v11)     #step 21: A3*B3
            v13 = oper(v12,ADD,v13)     #step 22: A0+A1*B1+A3*B3
            v10 = oper(v10,SUB,v1)      #step 23: n-3   counter= 1
            v6 = oper(v6,SUB,v1)        #step 13: 2n-1
            v7 = oper(v1,ADD,v7)        #step 14: 2+1 = 3
            v8 = oper(v6,DIV,v7)        #step 15: (2n-1)/3
            v11 = oper(v8,MUL,v11)      #step 16: (2n/2)*((2n-1)/3)
            v6 = oper(v6,SUB,v1)        #step 17: 2n-2
            v7 = oper(v1,ADD,v7)        #step 18: 3+1 = 4
            v9 = oper(v6,DIV,v7)        #step 19: (2n-2)/4
            v11 = oper(v9,MUL,v11)      #step 20: (2n-2)*((2n-1)/3)*((2n-2)/4)= A3
            v12 = oper(v23,MUL,v11)     #step 21: A3*B3
            v13 = oper(v12,ADD,v13)     #step 22: A0+A1*B1+A3*B3
            v10 = oper(v10,SUB,v1)      #step 23: n-4   counter = 0
            v24 = oper(v13,ADD,v24)     #step 24: A0+A1*B1+A3*B3+A5*B5 = B7
            v3 = oper(v1,ADD,v3)        #step 25: n=5  ready to compute B9!
            Bresult("B7", v24)
            times[0 if tables else 1][numdec] = cum_cycles*minutes_per_cycle
    plt.plot(numdecimals, times[0], marker='o', label="tables")
    plt.plot(numdecimals, times[1], marker='o', label="no tables")
    plt.grid()
    plt.legend()
    plt.title("Lovelace's computation of B7")
    plt.ylim(0);
    plt.ylabel("minutes");
    plt.xlabel("number of decimals")
    #plt.show()
    plt.savefig("Lovelace_B7.jpg", bbox_inches="tight")
    plt.close()

#-------------------------------------------------------------------------------------------------------
# graph the time it takes to do somewhat optimized calculations of B5 and B3
# without tables, but for a variety of digits to the right of the decimal point
#-------------------------------------------------------------------------------------------------------
    times = np.zeros((2, len(numdecimals)))
    for numdec in range(len(numdecimals)): #for the different number of decimals
        decimals = numdecimals[numdec]
    #*** compute B5 using Lovelace's instruction sequence optimized, with calls to our simulator
        cum_cycles = 0
    #initial engine conditions
        v1=1 * 10**decimals            #constant 1
        v2=2 * 10**decimals            #constant 2
        v3=3 * 10**decimals            #n=3, to compute the 3rd number, B(2n-1), or B5
        v4=v5=v6=v7=v8=v11=v12=v13=0 
                                    #uninitialized variables in the store are zero
        v21=int(1/6 * 10**decimals)    #B1  previously computed Bernoulli numbers
        v22=-int(1/30 * 10**decimals)  #B3
        v23=0                          #B5 will be put here
    #program: computes B5 = -A0 - A1B1 - A3B3
        v4=v5=v6 = oper(v2,MUL,v3)  #step 1: 2n
        v4 = oper(v4,SUB,v1)        #step 2: 2n-1
        v5 = oper(v5,ADD,v1)        #step 3: 2n+1
        v11 = oper(v4,DIV,v5)       #step 4: (2n-1)/(2n+1)
        v11 = oper(v11,DIV,v2)      #step 5: (1/2)((2n-1)/(2n+1)) = -A0
        v12 = oper(v21,MUL,v3)      #step 10: B1*n
        v12 = oper(v12,SUB,v11)     #step 11: -(1/2)(2n-1)/(2n+1) + B1*n
        v7 = oper(v1,ADD,v2)        #step 14: 2+1 = 3
        v8 = oper(v4,DIV,v7)        #step 15: (2n-1)/3
        v11 = oper(v8,MUL,v3)       #step 16: n*((2n-1)/3)
        v6 = oper(v6,SUB,v2)        #step 17: 2n-2
        v7 = oper(v1,ADD,v7)        #step 18: 3+1 = 4
        v9 = oper(v6,DIV,v7)        #step 19: (2n-2)/4
        v11 = oper(v9,MUL,v11)      #step 20: (2n-2)*((2n-1)/3)*((2n-2)/4) = A3
        v13 = oper(v22,MUL,v11)     #step 21: A3*B3
        v23 = oper(v12,ADD,v13)     #step 22: A0+A1*B1+A3*B3 = B5
        Bresult("B5", v23)
        times[0][numdec] = cum_cycles*minutes_per_cycle

    #*** compute B3 using Lovelace's instruction sequence optimized, with calls to our simulator
        cum_cycles = 0
    #initial engine conditions
        v1=1 * 10**decimals            #constant 1
        v2=2 * 10**decimals            #constant 2
        v3=2 * 10**decimals            #n=2, to compute the 2nd number, B(2n-1), or B3
        v4=v5=v6=v7=v8=v11=v12=v13=0 
                                    #uninitialized variables in the store are zero
        v21=int(1/6 * 10**decimals)    #B1  previously computed Bernoulli numbers
        v22=0                          #B3 will be put here
    #program: computes B3 = -A0 - A1B1
        v4=v5=v6 = oper(v2,MUL,v3)  #step 1: 2n
        v4 = oper(v4,SUB,v1)        #step 2: 2n-1
        v5 = oper(v5,ADD,v1)        #step 3: 2n+1
        v11 = oper(v4,DIV,v5)       #step 4: (2n-1)/(2n+1)
        v11 = oper(v11,DIV,v2)      #step 5: (1/2)((2n-1)/(2n+1))
        v12 = oper(v21,MUL,v3)      #step 10: n*B1
        v22 = oper(v12,SUB,v11)     #step 11: A0+A1*B1 = B3
        Bresult("B3", v22)
        times[1][numdec] = cum_cycles*minutes_per_cycle
    plt.plot(numdecimals, times[0], marker='o', label="B5")
    plt.plot(numdecimals, times[1], marker='o', label="B3")
    plt.grid()
    plt.legend()
    plt.title("calculations of B3 and B5 without tables")
    plt.ylim(0);
    plt.ylabel("minutes");
    plt.xlabel("number of decimals")
    #plt.show()
    plt.savefig("B3_B5.jpg", bbox_inches="tight")    
    exit()

#-------------------------------------------------------------------------------------------------------
# Create 2D graphs of average and min/max time and cycles/digit 
# for random tests of multiplication and division times 
# as a function of multiplicand and dividend length. 
# The multiplier is a random length random number.
# The divisor can either be that, or a fixed-length random number.
#-------------------------------------------------------------------------------------------------------

ntests = 5000 #of tests with random numbers
number_length = 30 #how many digits in a number
random_length_2nd_number = True #choose random length divisor or multiplier up to the size of the dividend or multiplicand?
divisor_length = 3 #this is the fixed divisor size if not random

fig, axes = plt.subplots(2,2, sharex=True, sharey="row", figsize=[10.0, 6.0], dpi=200) #four subplots:
# multiply on the left, divide on the right, time in minutes on top, cycles per digit on bottom
(ax_multime, ax_divtime, ax_mulcycles, ax_divcycles) = axes_list = list(np.concatenate(axes).flat)
fig.subplots_adjust(wspace=0.01, hspace=0.04, top=0.9, bottom=0.15, left=0.1, right=0.9)
for ax in axes_list: ax.grid(True)
ax_mulcycles.set(xlabel="digits in multiplicand")
ax_divcycles.set(xlabel="digits in dividend")
ax_multime.set(ylabel="minutes") #only the left graphs get y-axis labels
ax_mulcycles.set(ylabel="cycles per digit")

print("multiplication, avg, min, max")
print("ndigits,        ", end="")
if random_length_2nd_number:
    ax_multime.set_title("multiplication by random length")
else: 
    ax_multime.set_title("multiplication by n-digit numbers")
mul_total_table = graphline("with table", scale=minutes_per_cycle)
mul_digit_table = graphline("with table")
mul_total_notab = graphline("without table", scale=minutes_per_cycle)
mul_digit_notab = graphline("without table")
print()
for ndigits in  [*range(1,5), *range(5,number_length+1,1)]: #1 to 5, then 10, 15...
    mul_total_table.newpoint()
    mul_digit_table.newpoint() 
    mul_total_notab.newpoint() 
    mul_digit_notab.newpoint() 
    for testnum in range(ntests):
        multiplicand = rand(ndigits) 
        if random_length_2nd_number: multiplier_length = random.randint(1,ndigits)
        else: multiplier_length = ndigits
        multiplier = rand(multiplier_length)
        answer = multiply(multiplicand, multiplier, use_table=True)
        mul_total_table.updatepoint(answer["total_cycles"])
        mul_digit_table.updatepoint(answer["digit_cycles"])
        answer = multiply(multiplicand, multiplier, use_table=False)
        mul_total_notab.updatepoint(answer["total_cycles"])
        mul_digit_notab.updatepoint(answer["digit_cycles"])
    print(f"  {ndigits:2d},    ", end="")
    mul_total_table.closepoint(ndigits)
    mul_digit_table.closepoint(ndigits)
    mul_total_notab.closepoint(ndigits)
    mul_digit_notab.closepoint(ndigits)
    print()
mul_total_table.addline(ax_multime)
mul_total_notab.addline(ax_multime)
mul_digit_table.addline(ax_mulcycles)
mul_digit_notab.addline(ax_mulcycles)
ax_multime.legend(loc="upper left", fontsize="x-small")
#ax_mulcycles.legend(loc="upper left", fontsize="x-small")
print()

print("division, avg, min, max")
print("ndigits,        ", end="")
if random_length_2nd_number:
    ax_divtime.set_title(f"division by random-length")
else:
    ax_divtime.set_title(f"division by {divisor_length}-digit numbers")
div_total_table2 = graphline("with table; 2-digit selector", scale=minutes_per_cycle)
div_total_table1 = graphline("with table; 1-digit selector", scale=minutes_per_cycle)
div_digit_table2 = graphline("with table; 2-digit selector")
div_digit_table1 = graphline("with table; 1-digit selector")
div_total_notab = graphline("without table", scale=minutes_per_cycle)
div_digit_notab = graphline("without table")
print()
for ndigits in [*range(1,5), *range(5,number_length+1,1)]: #1 to 5, then 10, 15...
    div_total_table2.newpoint()
    div_total_table1.newpoint()
    div_digit_table2.newpoint() 
    div_digit_table1.newpoint() 
    div_total_notab.newpoint() 
    div_digit_notab.newpoint() 
    for testnum in range(ntests):
        dividend = rand(ndigits) #big dividends and small divisors make it work hard
        if random_length_2nd_number:
            divisor_length = random.randint(1,ndigits)
        divisor = rand(divisor_length)
        answer = divide(dividend, divisor, use_table=True, selector_digits=2)
        div_total_table2.updatepoint(answer["total_cycles"])
        div_digit_table2.updatepoint(answer["digit_cycles"])
        answer = divide(dividend, divisor, use_table=True, selector_digits=1)
        div_total_table1.updatepoint(answer["total_cycles"])
        div_digit_table1.updatepoint(answer["digit_cycles"])
        answer = divide(dividend, divisor, use_table=False)
        div_total_notab.updatepoint(answer["total_cycles"])
        div_digit_notab.updatepoint(answer["digit_cycles"])
    print(f"  {ndigits:2d},    ", end="")
    div_total_table2.closepoint(ndigits)
    div_total_table1.closepoint(ndigits)
    div_digit_table2.closepoint(ndigits)
    div_digit_table1.closepoint(ndigits)
    div_total_notab.closepoint(ndigits)
    div_digit_notab.closepoint(ndigits)
    print()
div_total_table2.addline(ax_divtime)
div_total_table1.addline(ax_divtime)
div_total_notab.addline(ax_divtime)
div_digit_table2.addline(ax_divcycles)
div_digit_table1.addline(ax_divcycles)
div_digit_notab.addline(ax_divcycles)
ax_divtime.legend(loc="upper left", fontsize="x-small")
#ax_divcycles.legend(loc="upper left", fontsize="x-small")
plt.show()