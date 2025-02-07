import pygame
import random

# -------------------------------------------------------
# Original Configuration
# -------------------------------------------------------

SCREEN_WIDTH = 432  # Window display width
SCREEN_HEIGHT = 768  # Window display height
RENDER_WIDTH = 1080  # Render resolution width (e.g., Full HD)
RENDER_HEIGHT = 1920  # Render resolution height (e.g., Full HD)
FPS = 60

PARTICLE_RADIUS = 15
PARTICLE_SPEED = 0.7
COLOR1_COUNT = 700  # Initial number of particles in COLOR1
COLOR2_COUNT = 700  # Initial number of particles in COLOR2
LAST_NUM_PARTICLES = 180  # Number of submissive particles left to trigger a reversal

MIDDLE_LAST_NUM_PARTICLES = 300  # Number of submissive particles for the middle phase
MIDDLE_GROUP = 8  # Time in seconds to switch to the middle phase

SECOND_LAST_NUM_PARTICLES = 50   # Number of submissive particles for the second to last phase
SECOND_LAST_GROUP = 11           # Time in seconds to switch to the second to last phase

FINAL_LAST_NUM_PARTICLES = 0     # Final threshold for the last phase
FINAL_LAST_GROUP = 31            # Time in seconds to switch to the final phase

# Colors and Names
COLOR2 = (0, 255, 255)     # First color (Cyan)
COLOR1 = (255, 69, 0)      # Second color (Orange Red)
COLOR2_NAME = "Cyan"
COLOR1_NAME = "Orange Red"

BACKGROUND_COLOR = (0, 0, 0)  # Background color

SEED = 33  # Seed for pseudo-random number generation

# Cooldown in seconds for conversions
CONVERSION_COOLDOWN = 0.06  

# Initial pause time
INITIAL_PAUSE_SECONDS = 3  

# Grid settings
GRID_SIZE = 50  

NEIGHBOR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]

# -------------------------------------------------------
# New Toggles and Font Sizes
# -------------------------------------------------------

SHOW_SCOREBOARD = True       # Toggle scoreboard display on/off
SHOW_WINNER_OVERLAY = True   # Toggle winner overlay on/off

# Smaller scoreboard font
SCOREBOARD_FONT_SIZE = 24

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Battle of Colors Simulation")

# Create a high-resolution surface for rendering
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

dominant_color = None
submissive_color = None

# -------------------------------------------------------
# Helper Function: Draw Text with a White Border
# -------------------------------------------------------
def draw_text_with_border(surface, text, font, text_color, border_color, pos, border_width=2):
    """
    Draws text with a border by first rendering the text in the border color
    several times with a small offset, then rendering the text in the main color.
    """
    # Loop over offsets (skipping the center)
    for dx in [-border_width, 0, border_width]:
        for dy in [-border_width, 0, border_width]:
            if dx != 0 or dy != 0:
                border_surface = font.render(text, True, border_color)
                surface.blit(border_surface, (pos[0] + dx, pos[1] + dy))
    # Now draw the main text
    text_surface = font.render(text, True, text_color)
    surface.blit(text_surface, pos)

# -------------------------------------------------------
# Pre-render circle surfaces
# -------------------------------------------------------
particle_surf_color1 = pygame.Surface((PARTICLE_RADIUS * 2, PARTICLE_RADIUS * 2), pygame.SRCALPHA)
pygame.draw.circle(particle_surf_color1, COLOR1, (PARTICLE_RADIUS, PARTICLE_RADIUS), PARTICLE_RADIUS)

particle_surf_color2 = pygame.Surface((PARTICLE_RADIUS * 2, PARTICLE_RADIUS * 2), pygame.SRCALPHA)
pygame.draw.circle(particle_surf_color2, COLOR2, (PARTICLE_RADIUS, PARTICLE_RADIUS), PARTICLE_RADIUS)

PARTICLE_SURF_MAP = {
    COLOR1: particle_surf_color1,
    COLOR2: particle_surf_color2
}

# -------------------------------------------------------
# Particle Class and Other Functions
# -------------------------------------------------------
class Particle:
    """Represents a single particle in the simulation."""
    __slots__ = ('x', 'y', 'radius', 'color', 'vx', 'vy', 'last_conversion_time')

    def __init__(self, x, y, radius, color, vx, vy):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.vx = vx
        self.vy = vy
        
        # Track when this particle last converted another (or was converted)
        self.last_conversion_time = float('-inf')

    def move(self):
        """Update position and handle wall collisions."""
        new_x = self.x + self.vx
        new_y = self.y + self.vy
        r = self.radius

        # Horizontal bounds
        if new_x - r < 0 or new_x + r > RENDER_WIDTH:
            self.vx = -self.vx
        else:
            self.x = new_x

        # Vertical bounds
        if new_y - r < 0 or new_y + r > RENDER_HEIGHT:
            self.vy = -self.vy
        else:
            self.y = new_y

    def draw(self, surface):
        """Draw using the pre-rendered circle surface for its color."""
        surf = PARTICLE_SURF_MAP[self.color]
        surface.blit(surf, (int(self.x - self.radius), int(self.y - self.radius)))

    def check_collision(self, other):
        """Check if this particle is colliding with another."""
        dx = self.x - other.x
        dy = self.y - other.y
        distance_squared = dx * dx + dy * dy
        combined_radius = self.radius + other.radius
        return distance_squared < (combined_radius * combined_radius)

    def resolve_collision(self, other, current_time):
        """Convert submissive particles to the dominant color if cooldown has elapsed."""
        global dominant_color, submissive_color

        if self.color == dominant_color and other.color == submissive_color:
            # Check if self is allowed to convert
            if (current_time - self.last_conversion_time) >= CONVERSION_COOLDOWN:
                other.color = dominant_color
                other.last_conversion_time = current_time
                self.last_conversion_time = current_time

        elif other.color == dominant_color and self.color == submissive_color:
            # Check if other is allowed to convert
            if (current_time - other.last_conversion_time) >= CONVERSION_COOLDOWN:
                self.color = dominant_color
                self.last_conversion_time = current_time
                other.last_conversion_time = current_time


def create_particles(color1_count, color2_count, speed, seed=None):
    """Create particles with specified counts for two colors."""
    if seed is not None:
        random.seed(seed)

    particles = []
    r = PARTICLE_RADIUS
    max_x = RENDER_WIDTH - r
    max_y = RENDER_HEIGHT - r

    for _ in range(color1_count):
        x = random.randint(r, max_x)
        y = random.randint(r, max_y)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        particles.append(Particle(x, y, r, COLOR1, vx, vy))

    for _ in range(color2_count):
        x = random.randint(r, max_x)
        y = random.randint(r, max_y)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        particles.append(Particle(x, y, r, COLOR2, vx, vy))

    return particles


def spatial_partitioning(particles):
    """Organize particles into a spatial grid to optimize collision detection."""
    grid = {}
    size = GRID_SIZE
    for p in particles:
        grid_x = int(p.x // size)
        grid_y = int(p.y // size)
        cell = (grid_x, grid_y)
        if cell not in grid:
            grid[cell] = []
        grid[cell].append(p)
    return grid


def check_collisions(grid, current_time):
    """Check for collisions using spatial partitioning."""
    for (cx, cy), cell_particles in grid.items():
        cp_len = len(cell_particles)
        # Collisions within the same cell
        for i in range(cp_len):
            p_i = cell_particles[i]
            for j in range(i + 1, cp_len):
                p_j = cell_particles[j]
                if p_i.check_collision(p_j):
                    p_i.resolve_collision(p_j, current_time)
        # Collisions with neighboring cells
        for ox, oy in NEIGHBOR_OFFSETS:
            neighbor = (cx + ox, cy + oy)
            if neighbor in grid:
                neighbor_particles = grid[neighbor]
                for p_i in cell_particles:
                    for p_j in neighbor_particles:
                        if p_i.check_collision(p_j):
                            p_i.resolve_collision(p_j, current_time)


def check_last_particles(particles, elapsed_time):
    """Check if the number of submissive particles is at the threshold and swap dominance."""
    global dominant_color, submissive_color

    # Determine the current threshold based on elapsed time
    if elapsed_time > FINAL_LAST_GROUP:
        threshold = FINAL_LAST_NUM_PARTICLES
    elif elapsed_time > SECOND_LAST_GROUP:
        threshold = SECOND_LAST_NUM_PARTICLES
    elif elapsed_time > MIDDLE_GROUP:
        threshold = MIDDLE_LAST_NUM_PARTICLES
    else:
        threshold = LAST_NUM_PARTICLES

    # Count how many submissive particles remain
    sc = submissive_color
    submissive_count = sum(1 for p in particles if p.color == sc)

    # If submissive particles reach the threshold, swap dominance
    if submissive_count <= threshold:
        dominant_color, submissive_color = submissive_color, dominant_color


def determine_initial_dominance():
    """Determine the initial dominant and submissive colors based on their starting counts."""
    global dominant_color, submissive_color
    if COLOR1_COUNT < COLOR2_COUNT:
        dominant_color, submissive_color = COLOR1, COLOR2
    elif COLOR2_COUNT < COLOR1_COUNT:
        dominant_color, submissive_color = COLOR2, COLOR1
    else:
        # Default if counts are equal
        dominant_color, submissive_color = COLOR1, COLOR2


def main():
    """Main simulation function."""
    global dominant_color, submissive_color

    determine_initial_dominance()

    # Create particles
    particles = create_particles(COLOR1_COUNT, COLOR2_COUNT, PARTICLE_SPEED, seed=SEED)

    # Clock for controlling FPS and tracking elapsed time
    clock = pygame.time.Clock()

    # Fonts for scoreboard and winner overlay
    scoreboard_font = pygame.font.SysFont(None, SCOREBOARD_FONT_SIZE)
    winner_font = pygame.font.SysFont(None, 72)

    # This will store whether we've declared a winner (so we only do it once).
    winner_declared = False
    winner_text = ""

    # Initial pause to view particles
    start_time = pygame.time.get_ticks()
    pause_duration = INITIAL_PAUSE_SECONDS * 1000
    while pygame.time.get_ticks() - start_time < pause_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                pygame.quit()
                return

        render_surface.fill(BACKGROUND_COLOR)
        for particle in particles:
            particle.draw(render_surface)

        # High-quality scaling to screen
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

    # Main simulation loop
    start_time = pygame.time.get_ticks()
    running = True
    while running:
        current_ticks = pygame.time.get_ticks()
        elapsed_time = (current_ticks - start_time) / 1000.0  # Elapsed time in seconds

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False

        # Check thresholds and swap dominance if necessary
        check_last_particles(particles, elapsed_time)

        # Spatial partitioning and collisions
        grid = spatial_partitioning(particles)
        check_collisions(grid, elapsed_time)

        # Clear and draw
        render_surface.fill(BACKGROUND_COLOR)
        
        # We'll track how many are each color
        color1_count = 0
        color2_count = 0
        
        for particle in particles:
            particle.move()
            particle.draw(render_surface)
            if particle.color == COLOR1:
                color1_count += 1
            else:
                color2_count += 1

        # Smooth scale for nice visuals
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # --------------------------------------------------
        # Scoreboard (if enabled)
        # --------------------------------------------------
        if SHOW_SCOREBOARD:
            # Prepare separate texts for the left and right sides
            left_text = f"{COLOR1_NAME}: {color1_count}"
            right_text = f"{COLOR2_NAME}: {color2_count}"
            # Left scoreboard (top left)
            left_pos = (15, 15)
            draw_text_with_border(screen, left_text, scoreboard_font, COLOR1, (255, 255, 255), left_pos)
            # Right scoreboard (top right)
            right_text_width, _ = scoreboard_font.size(right_text)
            right_pos = (SCREEN_WIDTH - right_text_width - 15, 15)
            draw_text_with_border(screen, right_text, scoreboard_font, COLOR2, (255, 255, 255), right_pos)

        # --------------------------------------------------
        # Check if one color is fully gone -> set winner
        # --------------------------------------------------
        if not winner_declared:
            if color1_count == 0:
                winner_declared = True
                winner_text = f"{COLOR2_NAME} WINS!"
            elif color2_count == 0:
                winner_declared = True
                winner_text = f"{COLOR1_NAME} WINS!"

        # --------------------------------------------------
        # Winner overlay (if enabled)
        # --------------------------------------------------
        # We do NOT pause or clear the background; just overlay the text
        if SHOW_WINNER_OVERLAY and winner_declared and winner_text:
            text_surface = winner_font.render(winner_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text_surface, text_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
