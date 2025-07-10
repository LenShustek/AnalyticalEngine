'''
   gear meshing analysis utility routines
   
   Most of these were initially writen by Google Gemini, then modified by me.
   The biggest change was to allow concentric locked gears with different diametral pitches.
   
   This was my first serious attempt to use an AI LLM as a coding assistant, and I am impressed!
   I was even able to ask it questions about why it did some things, and it came up with
   cogent explanations, although its tone is a bit sycophantic.
   
   Len Shustek, June 2025
'''
import math
epsilon = 1e-8 #floating point fuzz

def normalize_angle(angle_rad):
    """Normalizes an angle to be between -pi and pi."""
    return math.atan2(math.sin(angle_rad), math.cos(angle_rad))

def verify_gear_tooth_alignment_angular(name:str, axle_positions, teeth_counts, DPin, DPout, initial_angle=None, verbose=False):
    """
    Verifies if teeth of a 5-pinion gear train forming a loop can perfectly align
    with the tooth space of their meshing partners, by explicitly propagating angular positions.

    This function assumes:
    1. The distances between axle centers are already correct for perfect pitch circle tangency.
    2. The centers form a closed 5-sided polygon.
    3. Unless otherwise given, gear 0's (first gear's) reference tooth (e.g., tooth center)
       is initially aligned with the line connecting its axle (P0) to the axle of Gear 1 (P1).

    Args:
        axle_positions (list of tuples): A list of 5 (x, y) tuples representing the
                                         coordinates of the gear axles.
                                         e.g., [(x0, y0), (x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        teeth_counts (list of int): A list of 5 integers, where teeth_counts[i] is
                                    the number of teeth for gear i.
                                    e.g., [N0, N1, N2, N3, N4]
        DPin (list of float): The diametral pitch for the input of gears
        DPout (list of float): The diametral pitch for the output of gears
        initial_angle: the optional angle of the first gear's reference tooth counter-clockwise from the horizontal in degrees 

    Returns:
        tuple: (str, float, float, list) - A boolean indicating correct calculation,
                                          a string explaining the result,
                                          the final angular discrepancy in degrees from  horizontal,
                                          the final angular discrepancy in 'tooth pitches'
                                          the list of gear reference tooth angles from the horizontal in degrees
    """
    num_gears = 5
    if (len(axle_positions) < num_gears or len(teeth_counts) < num_gears or
        len(DPin) < num_gears or len(DPout) < num_gears):
        print( f"Error: {num_gears} gears are required for {name} analysis.")
        exit(0)

    # Verify geometric consistency of axle distances 
    tolerance_distance = 1e-4 # Tolerance for floating point comparisons of distances
    for i in range(num_gears):
        iplus1 = (i+1) % num_gears
        p1_coords = axle_positions[i]
        p2_coords = axle_positions[iplus1]
        measured_distance = math.sqrt((p2_coords[0] - p1_coords[0])**2 + (p2_coords[1] - p1_coords[1])**2)
        expected_distance = (teeth_counts[i]/DPout[i] + teeth_counts[iplus1]/DPin[iplus1])/2
        if abs(measured_distance - expected_distance) > tolerance_distance:
            print(f"  bad distance delta {measured_distance - expected_distance} from gear {iplus1} for {name} loop analysis")
            print(f"  points {p1_coords} and {p2_coords}")
            print(f"axle positions: {axle_positions}")
            print(f"tooth counts: {teeth_counts}")
            print(f"Geometric inconsistency: Measured distance between gear {i+1} "
                            f"and gear {(i+1)%num_gears+1} ({measured_distance:.6f}) "
                            f"does not match expected ({expected_distance:.6f}).")
            exit(0)

    current_gear_angles = [0.0] * num_gears #the angle from the horizontal of each gear's reference tooth
    p0_coords = axle_positions[0]
    p1_coords = axle_positions[1]
    if initial_angle is None: #gear 0's reference tooth is aligned with the line from G0 to G1
        initial_line_angle_01 = math.atan2(p1_coords[1] - p0_coords[1], p1_coords[0] - p0_coords[0])
    else: #gear 0's reference tooth is at the specified angle
        initial_line_angle_01 = initial_angle * math.pi / 180.0
        if verbose: print(f"analyzing with initial angle {initial_angle:.4f}")
    current_gear_angles[0] = initial_line_angle_01 # G0's reference tooth points this way
    initial_G0_angle = current_gear_angles[0] # Store the initial angle of G0 for final comparison

    # Propagate angular alignment through the chain: G0 -> G1 -> G2 -> G3 -> G4
    for i in range(num_gears - 1): # Iterate for 4 meshes (0-1, 1-2, 2-3, 3-4)
        current_gear_idx = i
        next_gear_idx = i + 1
        N_current = teeth_counts[current_gear_idx]
        N_next = teeth_counts[next_gear_idx]
        P_current = axle_positions[current_gear_idx]
        P_next = axle_positions[next_gear_idx]

        # Angle of the line of centers from current gear to next gear
        dx_forward = P_next[0] - P_current[0]
        dy_forward = P_next[1] - P_current[1]
        alpha_current_to_next = math.atan2(dy_forward, dx_forward)

        # Angle of the line of centers from next gear back to current gear
        alpha_next_to_current = normalize_angle(alpha_current_to_next + math.pi)

        # 1. Relative angle of current gear's reference tooth w.r.t. its 'forward' line of centers
        # This is how much G_current's reference tooth is rotated away from the line pointing to G_next
        relative_angle_current_to_forward_line = normalize_angle(current_gear_angles[current_gear_idx] - alpha_current_to_next)

        # 2. Calculate the required rotation for the next gear to mesh perfectly
        # For external gears:
        # - Direction is opposite (hence the negative sign for rotation_factor).
        # - Angular velocity ratio is N_current / N_next.
        # - For tooth-to-space meshing, there's a 0.5 tooth-pitch offset (pi / N_next radians)
        #   This offset means if G_current's tooth is at the mesh point, G_next's *space* must be there.

        # The angle of G_next's reference tooth relative to its *incoming* line of centers
        # (i.e., the line from P_next to P_current)
        required_relative_angle_next_to_incoming_line = (
            -relative_angle_current_to_forward_line * (N_current / N_next) # Inverse ratio and opposite direction
            + (math.pi / N_next) # Half-pitch offset for tooth-to-space alignment
        )
        required_relative_angle_next_to_incoming_line = normalize_angle(required_relative_angle_next_to_incoming_line)
        
        # 3. Convert required relative angle for next gear to its absolute angle
        current_gear_angles[next_gear_idx] = normalize_angle(required_relative_angle_next_to_incoming_line + alpha_next_to_current)

    # --- Final Check: G4 with G0 ---
    # We have current_gear_angles[4] (absolute angle of G4's reference tooth)
    # We need to see if it allows G0 to mesh perfectly with its initial angle.
    if verbose:
        current_gear_angle_degrees = [r * 180.0/math.pi for r in current_gear_angles]
        print(f"gear angles in degrees from horizontal:\n  {current_gear_angle_degrees}")
    N_G4 = teeth_counts[4]
    N_G0 = teeth_counts[0]
    P_G4 = axle_positions[4]
    P_G0 = axle_positions[0]

    # Angle of the line of centers from G4 to G0 (closing the loop)
    dx_40 = P_G0[0] - P_G4[0]
    dy_40 = P_G0[1] - P_G4[1]
    alpha_40 = math.atan2(dy_40, dx_40)
    # Angle of the line of centers from G0 back to G4
    alpha_04 = normalize_angle(alpha_40 + math.pi)
    #print(f"alpha_40 {alpha_40*180/math.pi}, alpha_04 {alpha_04*180/math.pi}")

    # Relative angle of G4's reference tooth w.r.t. its 'forward' line of centers (P4->P0)
    relative_angle_G4_to_forward_line = normalize_angle(current_gear_angles[4] - alpha_40)
    #print(f"relative_angle_G4_to_forward_line {relative_angle_G4_to_forward_line*180/math.pi} degrees") #correct

    # Calculate the required absolute angle of G0's reference tooth for perfect mesh with G4
    # (relative to its incoming line of centers, P0->P4)
    #print(f"-relative_angle_G4_to_forward_line * N_G4 / N_G0 {(-relative_angle_G4_to_forward_line * N_G4 / N_G0)*180/math.pi}")
    #print(f"-relative_angle_G4_to_forward_line {-relative_angle_G4_to_forward_line} radians ")
    required_relative_angle_G0_to_incoming_line = (-relative_angle_G4_to_forward_line * N_G4 / N_G0
        ) + (math.pi / N_G0) # Half-pitch offset for tooth-to-space alignment
    
    required_relative_angle_G0_to_incoming_line = normalize_angle(required_relative_angle_G0_to_incoming_line)
    #print(f"required_relative_angle_G0_to_incoming_line {required_relative_angle_G0_to_incoming_line*180/math.pi} degrees")

    calculated_G0_angle_for_closure = normalize_angle(required_relative_angle_G0_to_incoming_line + alpha_04)
    if verbose: print(f"calculated_G0_angle_for_closure {calculated_G0_angle_for_closure*180/math.pi} degrees ")

    # --- Compare initial G0 angle with calculated G0 angle for closure ---
    angular_discrepancy_rad = normalize_angle(calculated_G0_angle_for_closure - initial_G0_angle)
    # Convert discrepancy to 'tooth pitches' for G0
    G0_tooth_pitch_rad = 2 * math.pi / N_G0
    angular_discrepancy_rad = angular_discrepancy_rad % G0_tooth_pitch_rad #LJS
    angular_discrepancy_pitches = angular_discrepancy_rad / G0_tooth_pitch_rad
    angular_discrepancy_degrees = angular_discrepancy_rad * 180/math.pi
    
    # Normalize discrepancy to be between -0.5 and 0.5 pitches
    angular_discrepancy_pitches_normalized = angular_discrepancy_pitches % 1.0
    if angular_discrepancy_pitches_normalized > 0.5 + 1e-9:
         angular_discrepancy_pitches_normalized -= 1.0
    elif angular_discrepancy_pitches_normalized < -0.5 - 1e-9:
         angular_discrepancy_pitches_normalized += 1.0

    # For very small values, treat as zero
    tolerance_angular_rad = 1e-6
    if abs(abs(angular_discrepancy_rad) - math.pi) < tolerance_angular_rad: # Half-period match (pi rad, or 0.5 pitches)
        message = (f"A half-pitch misalignment occurs when the loop closes. Total angular discrepancy is {angular_discrepancy_rad:.4f} rad "
                   f"({angular_discrepancy_pitches_normalized:.4f} tooth pitches). "
                   f"This indicates that perfect simultaneous tooth-to-space alignment is impossible for this "
                   f"odd-numbered external gear train (the sum of teeth, {sum(teeth_counts)}, is odd), leading to binding or backlash.")
        print(message)
        exit(0)
    else: 
        message = (f"  the angular discrepancy is {angular_discrepancy_degrees:.4f} degrees, or "
                   f"{angular_discrepancy_pitches_normalized:.4f} tooth pitches ")
                      
    return message, angular_discrepancy_degrees, angular_discrepancy_pitches_normalized, [r*180.0/math.pi for r in current_gear_angles]

def compute_third_point_coordinates(p1: tuple, d1: float, p2: tuple, d2: float, verbose=False) -> list[tuple[float, float]] | None:
    """
    Computes the coordinates of a third point that is at specified distances
    from two given points. This is analogous to finding the intersection points
    of two circles.

    Args:
        p1 (tuple): The coordinates of the first point (x1, y1).
        d1 (float): The distance from the first point to the third point (radius of circle 1).
        p2 (tuple): The coordinates of the second point (x2, y2).
        d2 (float): The distance from the second point to the third point (radius of circle 2).

    Returns:
        list[tuple[float, float]] | None:
            A list of (x, y) tuples representing the intersection points.
            - Returns an empty list [] if there are no real intersection points.
            - Returns a list with one point [(x, y)] if the circles are tangent.
            - Returns a list with two points [(x1, y1), (x2, y2)] if there are two intersections.
            - Returns None if the two input points are identical and the distances are
              also identical and non-zero (infinite solutions, e.g., concentric circles
              with the same non-zero radius).
    """
    x1, y1 = p1
    x2, y2 = p2
    r1, r2 = d1, d2

    # Ensure distances are non-negative
    if r1 < 0 or r2 < 0:
        raise ValueError("Distances must be non-negative.")

    # Translate p1 to the origin (0,0) to simplify calculations
    # dx, dy represent the vector from p1 to p2
    dx = x2 - x1
    dy = y2 - y1

    # Calculate the distance between p1 and p2 (D)
    # This is the distance between the two circle centers
    D = math.sqrt(dx*dx + dy*dy)

    # Case 1: Circles are too far apart or one contains the other without touching
    # This means there are no real intersection points.
    if D > r1 + r2 or D < abs(r1 - r2):
        return []

    # Case 2: The two input points are identical (concentric circles)
    if D == 0:
        # If both radii are zero, the "third point" is simply the given point.
        if r1 == 0 and r2 == 0:
            return [(x1, y1)]
        # If radii are identical and non-zero, the circles are coincident,
        # leading to infinite intersection points. We return None to indicate this ambiguous case.
        elif r1 == r2:
            return None
        # If radii are different, concentric circles don't intersect (unless radii are zero).
        else:
            return []

    # --- Calculate intersection points for the general case ---

    # Calculate 'a': the distance from p1 along the line segment p1p2 to the
    # point where the common chord (line connecting intersection points)
    # intersects the line p1p2.
    # This formula is derived by subtracting the two circle equations.
    a = (D*D + r1*r1 - r2*r2) / (2*D)

    # Calculate 'h': the distance from the point 'a' (on line p1p2) perpendicular
    # to p1p2, to reach the intersection points. This is half the length of the
    # common chord.
    # It's derived using the Pythagorean theorem (h^2 + a^2 = r1^2).
    # We use a small epsilon for numerical stability to handle cases where
    # discriminant might be slightly negative due to floating point inaccuracies
    # when h should be exactly zero (single intersection point).
    discriminant = r1*r1 - a*a
    if discriminant < 0:
        # If it's very slightly negative due to floating point, treat as 0
        if abs(discriminant) < epsilon: # A small epsilon
            h = 0.0
        else:
            # Should not happen if previous checks for D > r1+r2 etc. are correct,
            # but included for robustness.
            return []
    else:
        h = math.sqrt(discriminant)

    # Calculate the coordinates of the point (x_mid, y_mid) on the line p1p2
    # that is 'a' distance from p1.
    # This point is the base of the perpendicular 'h' to the intersection points.
    x_mid = x1 + a * (dx / D)
    y_mid = y1 + a * (dy / D)

    # Calculate the unit vector perpendicular to the line p1p2.
    # This vector determines the direction to move 'h' distance from (x_mid, y_mid).
    # (dx/D, dy/D) is the unit vector along p1p2.
    # Perpendicular unit vector is (-dy/D, dx/D) or (dy/D, -dx/D).
    ux_perp = -dy / D
    uy_perp = dx / D
    solutions = []

    # First intersection point: (x_mid + h * ux_perp, y_mid + h * uy_perp)
    sol1_x = x_mid + h * ux_perp
    sol1_y = y_mid + h * uy_perp
    solutions.append((sol1_x, sol1_y))

    # Second intersection point: (x_mid - h * ux_perp, y_mid - h * uy_perp)
    # Only add if it's distinct from the first point (i.e., h > 0)
    if h != 0:
        sol2_x = x_mid - h * ux_perp
        sol2_y = y_mid - h * uy_perp
        solutions.append((sol2_x, sol2_y))

    return solutions

def set_by_distance(p1: tuple, d1: float, p2: tuple, d2: float, old:tuple):
    #find the point closest to an old point which is at the specified distances from two other points
    solutions = compute_third_point_coordinates(p1, d1, p2, d2)
    if not solutions:
        return []
    if math.dist(solutions[0], old) < math.dist(solutions[1], old):
        return solutions[0]
    else:
        return solutions[1]
    
def checkdist(name:str, newpos:tuple) -> tuple:
    if not newpos:
        print(f"can't find new consistent position for {name}")
        exit(0)
    return newpos

def fix_coord (c1:float, d1:float, c2:float, d2:float, dst:float):
    #fix coordinate c1 so that (c1,d1) is dst inches away from (c2,d2)
    #c and d  might be  x and y  or  y and x
    diffsq = dst**2 - (d1-d2)**2
    if diffsq < -epsilon**2:
        return None #no solution
    if diffsq < 0:
        return c1 #basically no change
    ans1 = c2 + math.sqrt(diffsq)
    ans2 = c2 - math.sqrt(diffsq)
    if abs(ans1-c1) < abs(ans2-c1): #choose the solution with the least change
        return ans1
    return ans2

def calculate_meshing_tooth_angle(
    NT1: int,        # Number of Teeth on Gear 1
    PT1: tuple,      #x,y center of gear 1
    NT2: int,        # Number of Teeth on Gear 2 
    PT2: tuple,      #x,y center of gear 2
    A1_degrees: float # Angle of a tooth on Gear 1 relative to horizontal (in degrees counter-clockwise)
) -> float: #the angle of a tooth on Gear 2 relative to the horizontal (in degrees counter-clockwise)
   
    # --- Step 1: Calculate the angle of the line of centers ---
    # Use math.atan2 to get the angle in radians, covering all four quadrants.
    # The angle is measured counter-clockwise from the positive X-axis.
    angle_line_of_centers_radians = math.atan2(PT2[1]-PT1[1], PT2[0]-PT1[0])

    # --- Step 2: Calculate the relative angle of Gear 1's tooth to the line of centers ---
    # This tells us how far the tooth on Gear 1 is rotated from the line
    # connecting its center to Gear 2's center.
    A1_radians = math.radians(A1_degrees)
    
    # The angle of Gear 1's tooth relative to the line of centers.
    # This is the angle from the line_of_centers_direction to the tooth_direction.
    relative_angle_G1_to_LC_radians = A1_radians - angle_line_of_centers_radians
    
    # --- Step 3: Calculate the relative angle of Gear 2's *valley* to the line of centers ---
    # When gears mesh, they rotate in opposite directions. The angular rotation
    # is inversely proportional to the number of teeth (gear ratio).
    # If Gear 1 rotates by 'x' radians relative to the line of centers,
    # Gear 2 will rotate by '-x * (NT1 / NT2)' radians relative to the line of centers.
    
    # The relative angle of Gear 2's tooth to the line of centers.
    # The negative sign accounts for the opposite direction of rotation.
    relative_angle_G2_to_LC_radians = -relative_angle_G1_to_LC_radians * (NT1/NT2)

    # --- Step 4: Calculate the absolute angle of Gear 2's tooth relative to horizontal ---
    # Add the angle of the line of centers back to get the absolute angle.
    A2_valley_radians = angle_line_of_centers_radians + relative_angle_G2_to_LC_radians
    A2_valley_degrees = math.degrees(A2_valley_radians)
    A2_degrees = A2_valley_degrees + 180.0/NT2 #adjust by half a tooth for tooth vs. valley

    # --- Step 5: Normalize the angle to be within 0 to 360 degrees ---
    # This ensures the output is consistent and easy to interpret.
    A2_degrees_normalized = A2_degrees % 360
    if A2_degrees_normalized < 0:
        A2_degrees_normalized += 360
    return A2_degrees_normalized
