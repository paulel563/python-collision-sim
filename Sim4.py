import pygame
import math
import random
import sys
import time

################################################################################
# ----------------------------- CONFIGURABLE VARS ----------------------------- #
################################################################################

# Window and render configuration
SCREEN_WIDTH = 432     # Display window width
SCREEN_HEIGHT = 768    # Display window height
RENDER_WIDTH = 1080    # Render resolution width
RENDER_HEIGHT = 1920   # Render resolution height
FPS = 60

# Simulation settings
INITIAL_PAUSE_TIME = 3.0   # seconds to pause (scene is frozen) before the ball starts moving
RANDOM_SEED = 1            # set to None for a different random each run
NUM_RINGS = 8             # number of rings
RING_GAP_DEGREES = 35      # gap size in degrees for each ring
RING_THICKNESS = 20        # thickness of each ring

# Radial gap between rings
RING_RADIAL_GAP = 40

# Ring rotation & dissolve properties
RING_ROTATION_SPEED = 2     # degrees per frame for ring rotation
RING_PARTICLE_COUNT = 50    # number of particles when a ring dissolves
RING_PARTICLE_SPEED = 1.0   # speed at which ring particles move outward
RING_PARTICLE_FADE_SPEED = 4  # how quickly particles fade (alpha decrement per frame)

# Alternate ring colors
RING_COLOR1 = (255, 200, 0)  # warm yellow
RING_COLOR2 = (0, 200, 255)  # cool blue

# Ball properties
BALL_SIZE = 15              # radius of the ball
BALL_COLOR = (255, 255, 255)  # ball color (white)
BALL_SPEED = 8.0           # initial ball speed (pixels per frame)
BALL_BOUNCINESS = 1.0       # multiplier for velocity on bounce (1.0 = elastic)

# Maximum random angle (in degrees) for bounce perturbation.
BOUNCE_MAX_ANGLE_DEGREES = 25  

# Increase in ball speed when passing through a gap.
BALL_SPEED_INCREMENT = 4.0

# Sound settings
COLLISION_SOUND_PATH = "collision7.mp3"  # collision sound file path
SOUND_VOLUME = 0.4         # volume for collision sound (0.0 - 1.0)
COLLISION_SOUND_DELAY = 0.055  # delay (in seconds) before collision sound can be played again

RING_POP_SOUND_PATH = "start.wav"  # sound file for ring pop/break
RING_POP_SOUND_VOLUME = 0.6        # volume for ring pop sound

# Text settings
TEXT_COLOR = (255, 255, 255)
TEXT_SIZE = 36           # font size for bounce count

# Behavior after escape
LINGER_TIME_AFTER_ESCAPE = 2.0  # seconds to wait after ball escapes before quitting

################################################################################
def is_in_gap(ball_angle, ring_angle, gap_degrees):
    """
    Returns True if ball_angle (in degrees) is within the gap defined by
    [ring_angle, ring_angle + gap_degrees] (angles wrapped mod360).
    """
    ball_angle %= 360
    start = ring_angle % 360
    end = (ring_angle + gap_degrees) % 360
    if start <= end:
        return start <= ball_angle <= end
    else:
        # Gap wraps past 360
        return ball_angle >= start or ball_angle <= end

def reflect_velocity(ball_vel, normal, bounciness=1.0):
    """
    Reflect a velocity vector (vx, vy) about a normalized normal (nx, ny).
    """
    vx, vy = ball_vel
    nx, ny = normal
    dot = vx * nx + vy * ny
    rx = vx - 2 * dot * nx
    ry = vy - 2 * dot * ny
    return (rx * bounciness, ry * bounciness)

def perturb_velocity(vx, vy):
    """
    After a collision, perturb the velocity by a random angle chosen uniformly
    from -BOUNCE_MAX_ANGLE_DEGREES to +BOUNCE_MAX_ANGLE_DEGREES.
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

    # Center point
    center_x = RENDER_WIDTH // 2
    center_y = RENDER_HEIGHT // 2

    # Create rings; the first ring starts at min_radius.
    min_radius = 60
    rings = []
    for i in range(NUM_RINGS):
        r = min_radius + i * (RING_THICKNESS + RING_RADIAL_GAP) + RING_THICKNESS / 2
        direction = 1 if (i % 2 == 0) else -1
        color = RING_COLOR1 if (i % 2 == 0) else RING_COLOR2
        rings.append(Ring(r, direction, i, color))

    # Initialize the ball at the center.
    init_angle = random.uniform(0, 2 * math.pi)
    ball_x = center_x
    ball_y = center_y
    vx = BALL_SPEED * math.cos(init_angle)
    vy = BALL_SPEED * math.sin(init_angle)
    bounce_count = 0

    # Track last collision sound time
    last_collision_sound_time = 0.0

    all_dissolved = False
    escape_time = None

    # Initial pause (ball and rings are static)
    start_time = time.time()
    paused = True

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        if paused and (time.time() - start_time >= INITIAL_PAUSE_TIME):
            paused = False

        if not paused and not all_dissolved:
            # Update rings
            for ring in rings:
                ring.update()

            # Move ball
            ball_x += vx
            ball_y += vy

            dx = ball_x - center_x
            dy = ball_y - center_y
            dist = math.hypot(dx, dy)
            ball_angle_deg = math.degrees(math.atan2(dy, dx))

            collision_happened = False

            for ring in rings:
                if collision_happened or ring.state != "active":
                    continue

                inner = ring.radius - RING_THICKNESS / 2
                outer = ring.radius + RING_THICKNESS / 2

                if inner <= dist <= outer:
                    # If ball's angle is within the gap, consider it a successful pass.
                    if is_in_gap(ball_angle_deg, ring.rotation_angle, RING_GAP_DEGREES):
                        ring.start_dissolve()
                        if ring_pop_sound:
                            ring_pop_sound.play()
                        # Increase ball speed
                        current_speed = math.hypot(vx, vy)
                        new_speed = current_speed + BALL_SPEED_INCREMENT
                        angle_current = math.atan2(vy, vx)
                        vx = new_speed * math.cos(angle_current)
                        vy = new_speed * math.sin(angle_current)
                    else:
                        # Otherwise, reflect the ball.
                        if dist != 0:
                            nx = dx / dist
                            ny = dy / dist
                            vx, vy = reflect_velocity((vx, vy), (nx, ny), BALL_BOUNCINESS)
                            vx, vy = perturb_velocity(vx, vy)
                            bounce_count += 1
                            if collision_sound and (time.time() - last_collision_sound_time >= COLLISION_SOUND_DELAY):
                                collision_sound.play()
                                last_collision_sound_time = time.time()
                    collision_happened = True  # Only one collision per frame

            if all(r.state == "dissolved" for r in rings):
                all_dissolved = True
                escape_time = time.time()

        if all_dissolved and escape_time is not None:
            if time.time() - escape_time > LINGER_TIME_AFTER_ESCAPE:
                running = False

        # Rendering
        render_surface.fill((0, 0, 0))
        for ring in reversed(rings):
            if ring.state == "active":
                outer_radius = int(ring.radius + RING_THICKNESS / 2)
                inner_radius = int(ring.radius - RING_THICKNESS / 2)
                pygame.draw.circle(render_surface, ring.color, (center_x, center_y), outer_radius)
                pygame.draw.circle(render_surface, (0, 0, 0), (center_x, center_y), inner_radius)

                # Draw gap polygon for visual clarity.
                gap_points = []
                steps = 24
                start_rad = math.radians(ring.rotation_angle)
                end_rad = math.radians(ring.rotation_angle + RING_GAP_DEGREES)
                for step in range(steps + 1):
                    t = start_rad + (end_rad - start_rad) * (step / steps)
                    x = center_x + (outer_radius + 1) * math.cos(t)
                    y = center_y + (outer_radius + 1) * math.sin(t)
                    gap_points.append((x, y))
                for step in range(steps, -1, -1):
                    t = start_rad + (end_rad - start_rad) * (step / steps)
                    x = center_x + (inner_radius - 1) * math.cos(t)
                    y = center_y + (inner_radius - 1) * math.sin(t)
                    gap_points.append((x, y))
                pygame.draw.polygon(render_surface, (0, 0, 0), gap_points)
            elif ring.state == "dissolving":
                for p in ring.particles:
                    a = math.radians(p["base_angle"])
                    rx = center_x + p["radius"] * math.cos(a)
                    ry = center_y + p["radius"] * math.sin(a)
                    alpha = max(0, min(255, int(p["alpha"])))
                    color = (ring.color[0], ring.color[1], ring.color[2], alpha)
                    surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                    pygame.draw.circle(surf, color, (5, 5), 3)
                    render_surface.blit(surf, (rx - 5, ry - 5))

        pygame.draw.circle(render_surface, BALL_COLOR, (int(ball_x), int(ball_y)), BALL_SIZE)
        text_surf = font.render(f"Bounces: {bounce_count}", True, TEXT_COLOR)
        text_rect = text_surf.get_rect(midtop=(RENDER_WIDTH // 2, 20))
        render_surface.blit(text_surf, text_rect)
        scaled = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
