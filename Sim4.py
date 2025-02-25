import pygame
import math
import random
import sys
import time

################################################################################
# ----------------------------- CONFIGURABLE VARS ----------------------------- #
################################################################################

# Window and render configuration
SCREEN_WIDTH = 432    # Display window width
SCREEN_HEIGHT = 768   # Display window height
RENDER_WIDTH = 1080   # Render resolution width
RENDER_HEIGHT = 1920  # Render resolution height
FPS = 60

# Simulation settings
INITIAL_PAUSE_TIME = 3.0    # seconds to pause (scene is frozen) before the ball starts moving
RANDOM_SEED = 1             # set to None for a different random each run
NUM_RINGS = 10              # number of rings
RING_GAP_DEGREES = 35       # nominal gap size in degrees for each ring
RING_THICKNESS = 18         # thickness of each ring

# New variable: gap (in pixels) between each ring (radially)
RING_RADIAL_GAP = 30        # gap between rings

# Extra margins (in degrees) to ensure gap drawing is clean.
GAP_DRAW_MARGIN = 2.0       # extra margin when drawing the gap (to cover stray pixels)

# For collision detection we enforce a strict gap:
# if the ball is too near the endpoints, it is not considered safely in the gap.
GAP_COLLISION_ENDPOINT_MARGIN = 3.0  # degrees subtracted from each end for collision

# New variable: if the ball is within this many pixels of a ring's outer boundary, and moving outward,
# we consider it passing through.
PASS_THRESHOLD = 3.0

# New variable: a small offset so that the ball doesn't spawn exactly at the center.
BALL_INITIAL_OFFSET = 1

# Ring rotation & dissolve properties
RING_ROTATION_SPEED = 2     # degrees per frame for ring rotation
RING_PARTICLE_COUNT = 50    # number of particles when a ring dissolves
RING_PARTICLE_SPEED = 1.0   # speed at which ring particles move outward
RING_PARTICLE_FADE_SPEED = 5  # how quickly particles fade (alpha decrement per frame)

# Alternate ring colors (rings will alternate between these two)
RING_COLOR1 = (255, 200, 0)   # e.g. a warm yellow
RING_COLOR2 = (0, 200, 255)   # e.g. a cool blue

# Ball properties
BALL_SIZE = 15              # radius of the ball
BALL_COLOR = (255, 255, 255)  # ball color (white)
BALL_SPEED = 9.0           # initial ball speed (pixels per frame)
BALL_BOUNCINESS = 1.0       # multiplier for velocity on bounce (1.0 = elastic)

# Maximum random angle (in degrees) for bounce perturbation.
BOUNCE_MAX_ANGLE_DEGREES = 20  

# New variable: increment to add to ball speed each time it passes a ring.
BALL_SPEED_INCREMENT = 3.0

# Sound settings
COLLISION_SOUND_PATH = "collision7.mp3"  # collision sound file path
SOUND_VOLUME = 0.5         # volume for collision sound (0.0 - 1.0)
COLLISION_SOUND_DELAY = 0.05  # delay (in seconds) before collision sound can be played again

RING_POP_SOUND_PATH = "start.wav"  # sound file for ring pop/break
RING_POP_SOUND_VOLUME = 0.5        # volume for ring pop sound

# Text settings
TEXT_COLOR = (255, 255, 255)
TEXT_SIZE = 36           # font size for bounce count

# Behavior after escape
LINGER_TIME_AFTER_ESCAPE = 2.0  # seconds to wait after ball escapes before quitting

# Tolerance added for angle comparisons (in degrees)
# (Set low so the gap detection is not too forgiving.)
ANGLE_TOLERANCE = 5.0

################################################################################
def angle_in_safe_gap(ball_angle, ring_angle, gap_degrees, endpoint_margin, tolerance=ANGLE_TOLERANCE):
    """
    Returns True if ball_angle (in degrees) is within the gap,
    excluding endpoint_margin from both ends but with a small tolerance.
    """
    ball_angle %= 360
    safe_start = (ring_angle + endpoint_margin) % 360
    safe_end = (ring_angle + gap_degrees - endpoint_margin) % 360
    if safe_start <= safe_end:
        return (safe_start - tolerance) <= ball_angle <= (safe_end + tolerance)
    else:
        return ball_angle >= (safe_start - tolerance) or ball_angle <= (safe_end + tolerance)

def reflect_velocity(ball_vel, normal, bounciness=1.0):
    """
    Reflect a velocity vector (vx, vy) about a normalized normal (nx, ny).
    bounciness multiplies the result.
    """
    vx, vy = ball_vel
    nx, ny = normal
    dot = vx * nx + vy * ny
    rx = vx - 2 * dot * nx
    ry = vy - 2 * dot * ny
    return (rx * bounciness, ry * bounciness)

def perturb_velocity(vx, vy):
    """
    After a collision, perturb the velocity by a small random angle.
    The angle is chosen uniformly from -BOUNCE_MAX_ANGLE_DEGREES to +BOUNCE_MAX_ANGLE_DEGREES.
    """
    angle = math.atan2(vy, vx)
    angle_offset = math.radians(random.uniform(-BOUNCE_MAX_ANGLE_DEGREES, BOUNCE_MAX_ANGLE_DEGREES))
    new_angle = angle + angle_offset
    mag = math.hypot(vx, vy)
    return (mag * math.cos(new_angle), mag * math.sin(new_angle))

class Ring:
    """
    Represents a ring with a given radius, rotation, color, and dissolve state.
    """
    def __init__(self, radius, direction, index, color):
        self.radius = radius
        self.direction = direction  # +1 or -1
        self.rotation_angle = 0
        self.state = "active"       # "active", "dissolving", or "dissolved"
        self.particles = []
        self.index = index
        self.color = color

    def update(self):
        if self.state == "active":
            self.rotation_angle = (self.rotation_angle + RING_ROTATION_SPEED * self.direction) % 360
        elif self.state == "dissolving":
            new_particles = []
            for p in self.particles:
                p["radius"] += RING_PARTICLE_SPEED
                p["alpha"] -= RING_PARTICLE_FADE_SPEED
                if p["alpha"] > 0:
                    new_particles.append(p)
            self.particles = new_particles
            if not self.particles:
                self.state = "dissolved"

    def start_dissolve(self):
        self.state = "dissolving"
        self.particles = []
        for i in range(RING_PARTICLE_COUNT):
            angle_deg = (360 / RING_PARTICLE_COUNT) * i
            self.particles.append({
                "base_angle": angle_deg,
                "radius": self.radius,
                "alpha": 255
            })

def main():
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Bouncing Ball Prison")
    clock = pygame.time.Clock()

    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

    # Load sounds
    try:
        collision_sound = pygame.mixer.Sound(COLLISION_SOUND_PATH)
        collision_sound.set_volume(SOUND_VOLUME)
    except Exception as e:
        print("Warning: Could not load collision sound:", e)
        collision_sound = None

    try:
        ring_pop_sound = pygame.mixer.Sound(RING_POP_SOUND_PATH)
        ring_pop_sound.set_volume(RING_POP_SOUND_VOLUME)
    except Exception as e:
        print("Warning: Could not load ring pop sound:", e)
        ring_pop_sound = None

    font = pygame.font.SysFont(None, TEXT_SIZE)

    # Set up center point
    center_x = RENDER_WIDTH // 2
    center_y = RENDER_HEIGHT // 2

    # Create rings: space them radially using RING_RADIAL_GAP.
    min_radius = 60  # inner edge of the first ring
    rings = []
    for i in range(NUM_RINGS):
        # Compute the center of the ring so that its inner edge is at min_radius + i*(RING_THICKNESS+RING_RADIAL_GAP)
        r = min_radius + i * (RING_THICKNESS + RING_RADIAL_GAP) + RING_THICKNESS / 2
        direction = 1 if (i % 2 == 0) else -1
        color = RING_COLOR1 if (i % 2 == 0) else RING_COLOR2
        rings.append(Ring(r, direction, i, color))

    # Initialize the ball slightly offset from the center to avoid immediate collision.
    init_angle = random.uniform(0, 2 * math.pi)
    ball_x = center_x + BALL_INITIAL_OFFSET * math.cos(init_angle)
    ball_y = center_y + BALL_INITIAL_OFFSET * math.sin(init_angle)
    vx = BALL_SPEED * math.cos(init_angle)
    vy = BALL_SPEED * math.sin(init_angle)
    bounce_count = 0

    # Variable to track the last time a collision sound was played
    last_collision_sound_time = 0.0

    all_dissolved = False
    escape_time = None

    # Initial pause: scene is rendered but ball and rings remain static.
    start_time = time.time()
    paused = True

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # seconds elapsed

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        if paused and (time.time() - start_time >= INITIAL_PAUSE_TIME):
            paused = False

        # Only check collisions if not paused and rings still active
        if not paused and not all_dissolved:
            # Update active rings
            for ring in rings:
                ring.update()

            # Move the ball
            ball_x += vx
            ball_y += vy

            # Compute values once per frame
            dx = ball_x - center_x
            dy = ball_y - center_y
            dist_from_center = math.hypot(dx, dy)
            ball_angle_deg = math.degrees(math.atan2(dy, dx))
            # Radial velocity: projection of ball velocity onto the vector from center to ball
            radial_velocity = (vx * dx + vy * dy) / (dist_from_center if dist_from_center != 0 else 1)

            collision_happened = False  # to ensure only one ring collision per frame

            for ring in rings:
                if collision_happened:
                    break

                if ring.state != "active":
                    continue

                ring_inner = ring.radius - RING_THICKNESS / 2
                ring_outer = ring.radius + RING_THICKNESS / 2

                # Case 1: Ball is within the ring's thickness.
                if ring_inner <= dist_from_center <= ring_outer:
                    if angle_in_safe_gap(ball_angle_deg, ring.rotation_angle, RING_GAP_DEGREES, GAP_COLLISION_ENDPOINT_MARGIN):
                        # Check if ball is near the outer boundary (with tolerance) and moving outward.
                        if radial_velocity > 0 and abs(ring_outer - dist_from_center) <= PASS_THRESHOLD:
                            ring.start_dissolve()
                            if ring_pop_sound:
                                ring_pop_sound.play()
                            current_speed = math.hypot(vx, vy)
                            new_speed = current_speed + BALL_SPEED_INCREMENT
                            angle_current = math.atan2(vy, vx)
                            vx = new_speed * math.cos(angle_current)
                            vy = new_speed * math.sin(angle_current)
                            collision_happened = True
                    else:
                        # Ball colliding with the solid part: reflect the velocity.
                        if dist_from_center != 0:
                            nx = dx / dist_from_center
                            ny = dy / dist_from_center
                            vx, vy = reflect_velocity((vx, vy), (nx, ny), BALL_BOUNCINESS)
                            vx, vy = perturb_velocity(vx, vy)
                            bounce_count += 1
                            if collision_sound and (time.time() - last_collision_sound_time >= COLLISION_SOUND_DELAY):
                                collision_sound.play()
                                last_collision_sound_time = time.time()
                            collision_happened = True

                # Case 2: Ball has nearly moved past the outer boundary.
                elif dist_from_center >= ring_outer - PASS_THRESHOLD:
                    if angle_in_safe_gap(ball_angle_deg, ring.rotation_angle, RING_GAP_DEGREES, GAP_COLLISION_ENDPOINT_MARGIN):
                        if ring.state == "active":
                            ring.start_dissolve()
                            if ring_pop_sound:
                                ring_pop_sound.play()
                            current_speed = math.hypot(vx, vy)
                            new_speed = current_speed + BALL_SPEED_INCREMENT
                            angle_current = math.atan2(vy, vx)
                            vx = new_speed * math.cos(angle_current)
                            vy = new_speed * math.sin(angle_current)
                            collision_happened = True

            if all(r.state == "dissolved" for r in rings):
                all_dissolved = True
                escape_time = time.time()

        if all_dissolved and escape_time is not None:
            if time.time() - escape_time > LINGER_TIME_AFTER_ESCAPE:
                running = False

        # RENDERING
        render_surface.fill((0, 0, 0))
        for ring in reversed(rings):
            if ring.state == "active":
                outer_radius = int(ring.radius + RING_THICKNESS / 2)
                inner_radius = int(ring.radius - RING_THICKNESS / 2)
                pygame.draw.circle(render_surface, ring.color, (center_x, center_y), outer_radius)
                pygame.draw.circle(render_surface, (0, 0, 0), (center_x, center_y), inner_radius)

                # Draw gap polygon
                gap_points = []
                gap_steps = 24
                start_gap_rad = math.radians(ring.rotation_angle - GAP_DRAW_MARGIN)
                end_gap_rad = math.radians(ring.rotation_angle + RING_GAP_DEGREES + GAP_DRAW_MARGIN)
                for step in range(gap_steps + 1):
                    t = start_gap_rad + (end_gap_rad - start_gap_rad) * (step / gap_steps)
                    xg = center_x + (outer_radius + 1) * math.cos(t)
                    yg = center_y + (outer_radius + 1) * math.sin(t)
                    gap_points.append((xg, yg))
                for step in range(gap_steps, -1, -1):
                    t = start_gap_rad + (end_gap_rad - start_gap_rad) * (step / gap_steps)
                    xg = center_x + (inner_radius - 1) * math.cos(t)
                    yg = center_y + (inner_radius - 1) * math.sin(t)
                    gap_points.append((xg, yg))
                pygame.draw.polygon(render_surface, (0, 0, 0), gap_points)
            elif ring.state == "dissolving":
                # Draw dissolving particles.
                for p in ring.particles:
                    angle_rad = math.radians(p["base_angle"])
                    rx = center_x + p["radius"] * math.cos(angle_rad)
                    ry = center_y + p["radius"] * math.sin(angle_rad)
                    alpha = max(0, min(255, int(p["alpha"])))
                    particle_color = (ring.color[0], ring.color[1], ring.color[2], alpha)
                    particle_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                    pygame.draw.circle(particle_surf, particle_color, (5, 5), 3)
                    render_surface.blit(particle_surf, (rx - 5, ry - 5))

        pygame.draw.circle(render_surface, BALL_COLOR, (int(ball_x), int(ball_y)), BALL_SIZE)
        text_surf = font.render(f"Bounces: {bounce_count}", True, TEXT_COLOR)
        text_rect = text_surf.get_rect(midtop=(RENDER_WIDTH // 2, 20))
        render_surface.blit(text_surf, text_rect)
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
