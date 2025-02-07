import pygame
import random

# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

SCREEN_WIDTH = 432
SCREEN_HEIGHT = 768
RENDER_WIDTH = 1080
RENDER_HEIGHT = 1920
FPS = 60

# Collision bounding circle (used for letter collision)
PARTICLE_RADIUS = 40

# Movement speed
PARTICLE_SPEED = 0.5

# Initial counts for letters
LETTER1_COUNT = 250
LETTER2_COUNT = 250

# Threshold-based phase switching
LAST_NUM_PARTICLES = 90
MIDDLE_LAST_NUM_PARTICLES = 200
MIDDLE_GROUP = 8
SECOND_LAST_NUM_PARTICLES = 50
SECOND_LAST_GROUP = 11
FINAL_LAST_NUM_PARTICLES = 0
FINAL_LAST_GROUP = 31

# These are purely for dominance/collision logic (not drawn as colors)
LOGIC_COLOR1 = (255, 69, 0)      # For LETTER1 in logic
LOGIC_COLOR2 = (0, 255, 255)     # For LETTER2 in logic

# Letters (and scoreboard labels) to fight
LETTER1 = "Q"  # "dominant" or "submissive" type 1
LETTER2 = "V"  # "dominant" or "submissive" type 2

# Actual display colors for each letter
LETTER1_COLOR = (151, 215, 0)  # First color (Wicked Green)
LETTER2_COLOR = (255, 102, 196)  # Second color (Wicket Pink)

BACKGROUND_COLOR = (0, 0, 0)

SEED = 4
CONVERSION_COOLDOWN = 0.06
INITIAL_PAUSE_SECONDS = 3
GRID_SIZE = 50

NEIGHBOR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]

# Toggles
SHOW_SCOREBOARD = True       
SHOW_WINNER_OVERLAY = True  

# Fonts
SCOREBOARD_FONT_SIZE = 24

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Letter Battle Simulation")

# High-resolution render surface
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

# For internal logic only:
dominant_color = None  # will be either LOGIC_COLOR1 or LOGIC_COLOR2
submissive_color = None  # likewise

#
# ------------------------------------------------------------------------
# Function to render text with a simple white outline (stroke)
# ------------------------------------------------------------------------
#
def render_text_with_outline(font, text, text_color, outline_color=(255, 255, 255), outline_width=2):
    """
    Renders 'text' in 'text_color' with a thick 'outline_color' stroke.
    Returns a new Surface that you can blit onto the screen.
    """
    # First render the base text (no outline)
    base_surface = font.render(text, True, text_color)
    
    # To make an outline, we'll create a slightly larger surface
    # and render the outline text around the base text.
    width, height = base_surface.get_size()
    outline_surface = pygame.Surface((width + 2*outline_width, height + 2*outline_width), pygame.SRCALPHA)
    
    # Render the outline by offsetting the text in 8 directions + center
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            # skip the (0,0) offset where we'll place the base text
            if dx == 0 and dy == 0:
                continue
            outline_surface.blit(font.render(text, True, outline_color),
                                 (dx + outline_width, dy + outline_width))
    
    # Finally, blit the base text in the center
    outline_surface.blit(base_surface, (outline_width, outline_width))
    return outline_surface


#
# ------------------------------------------------------------------------
# Create letter surfaces for each letter in its respective color
# ------------------------------------------------------------------------
#

item_font_size = PARTICLE_RADIUS * 2  # approximate letter size
item_font = pygame.font.SysFont(None, item_font_size, bold=True)

letter_surf_1 = item_font.render(LETTER1, True, LETTER1_COLOR)
letter_surf_2 = item_font.render(LETTER2, True, LETTER2_COLOR)

# For collision/dominance logic, we still map "logic color" -> letter surface
ITEM_SURF_MAP = {
    LOGIC_COLOR1: letter_surf_1,
    LOGIC_COLOR2: letter_surf_2
}


class Item:
    """
    A 'letter item' that behaves just like the old particles,
    but is drawn as a bold colored letter instead of a circle.
    """
    __slots__ = ('x', 'y', 'radius', 'color', 'vx', 'vy', 'last_conversion_time')
    
    def __init__(self, x, y, radius, color, vx, vy):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color  # This is either LOGIC_COLOR1 or LOGIC_COLOR2
        self.vx = vx
        self.vy = vy
        self.last_conversion_time = float('-inf')

    def move(self):
        """Keep the item within the boundaries, bouncing as needed."""
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
        """
        Draw the item (the letter) on the surface.
        We'll center the letter at (self.x, self.y).
        """
        letter_surf = ITEM_SURF_MAP[self.color]
        surface.blit(letter_surf, (int(self.x - self.radius), int(self.y - self.radius)))

    def check_collision(self, other):
        """Circle-based collision check (distance < sum of radii)."""
        dx = self.x - other.x
        dy = self.y - other.y
        distance_sq = dx * dx + dy * dy
        combined_radius = self.radius + other.radius
        return distance_sq < (combined_radius * combined_radius)

    def resolve_collision(self, other, current_time):
        """
        If I'm dominant and the other is submissive (or vice versa),
        and the cooldown is met, convert the other item to my color.
        """
        global dominant_color, submissive_color

        if self.color == dominant_color and other.color == submissive_color:
            if (current_time - self.last_conversion_time) >= CONVERSION_COOLDOWN:
                other.color = dominant_color
                other.last_conversion_time = current_time
                self.last_conversion_time = current_time
        elif other.color == dominant_color and self.color == submissive_color:
            if (current_time - other.last_conversion_time) >= CONVERSION_COOLDOWN:
                self.color = dominant_color
                self.last_conversion_time = current_time
                other.last_conversion_time = current_time


def create_items(count1, count2, speed, seed=None):
    """Create Item objects for each letter type."""
    if seed is not None:
        random.seed(seed)
    
    items = []
    r = PARTICLE_RADIUS
    max_x = RENDER_WIDTH - r
    max_y = RENDER_HEIGHT - r

    # Letter1 items
    for _ in range(count1):
        x = random.randint(r, max_x)
        y = random.randint(r, max_y)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        items.append(Item(x, y, r, LOGIC_COLOR1, vx, vy))

    # Letter2 items
    for _ in range(count2):
        x = random.randint(r, max_x)
        y = random.randint(r, max_y)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        items.append(Item(x, y, r, LOGIC_COLOR2, vx, vy))

    return items


def spatial_partitioning(items):
    """Organize items into a spatial grid for efficient collision checks."""
    grid = {}
    size = GRID_SIZE
    for it in items:
        grid_x = int(it.x // size)
        grid_y = int(it.y // size)
        cell = (grid_x, grid_y)
        if cell not in grid:
            grid[cell] = []
        grid[cell].append(it)
    return grid


def check_collisions(grid, current_time):
    """Check collisions between items in each cell and neighboring cells."""
    for (cx, cy), cell_items in grid.items():
        c_len = len(cell_items)
        for i in range(c_len):
            it_i = cell_items[i]
            for j in range(i + 1, c_len):
                it_j = cell_items[j]
                if it_i.check_collision(it_j):
                    it_i.resolve_collision(it_j, current_time)
        
        for ox, oy in NEIGHBOR_OFFSETS:
            neighbor = (cx + ox, cy + oy)
            if neighbor in grid:
                neighbor_items = grid[neighbor]
                for it_i in cell_items:
                    for it_j in neighbor_items:
                        if it_i.check_collision(it_j):
                            it_i.resolve_collision(it_j, current_time)


def check_last_items(items, elapsed_time):
    """
    If the submissive items drop below a threshold, swap dominance.
    This logic is unchanged from the original circle version.
    """
    global dominant_color, submissive_color

    if elapsed_time > FINAL_LAST_GROUP:
        threshold = FINAL_LAST_NUM_PARTICLES
    elif elapsed_time > SECOND_LAST_GROUP:
        threshold = SECOND_LAST_NUM_PARTICLES
    elif elapsed_time > MIDDLE_GROUP:
        threshold = MIDDLE_LAST_NUM_PARTICLES
    else:
        threshold = LAST_NUM_PARTICLES

    sc = submissive_color
    submissive_count = sum(1 for it in items if it.color == sc)
    if submissive_count <= threshold:
        dominant_color, submissive_color = submissive_color, dominant_color


def determine_initial_dominance():
    """
    Decide which letter is initially dominant based on the counts.
    (Using LOGIC_COLOR1/LOGIC_COLOR2 for internal logic.)
    """
    global dominant_color, submissive_color
    if LETTER1_COUNT < LETTER2_COUNT:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2
    elif LETTER2_COUNT < LETTER1_COUNT:
        dominant_color, submissive_color = LOGIC_COLOR2, LOGIC_COLOR1
    else:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2


def main():
    global dominant_color, submissive_color

    determine_initial_dominance()

    # Create our letter items
    items = create_items(LETTER1_COUNT, LETTER2_COUNT, PARTICLE_SPEED, seed=SEED)

    clock = pygame.time.Clock()

    # Fonts for scoreboard & winner overlay
    scoreboard_font = pygame.font.SysFont(None, SCOREBOARD_FONT_SIZE)
    winner_font = pygame.font.SysFont(None, 72)

    winner_declared = False
    winner_text = ""

    # Initial pause
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
        for it in items:
            it.draw(render_surface)

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

    # Main simulation
    simulation_start = pygame.time.get_ticks()
    running = True
    while running:
        current_ticks = pygame.time.get_ticks()
        elapsed_time = (current_ticks - simulation_start) / 1000.0

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
               event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False

        # Time-based dominance logic
        check_last_items(items, elapsed_time)

        # Collisions
        grid = spatial_partitioning(items)
        check_collisions(grid, elapsed_time)

        # Draw everything
        render_surface.fill(BACKGROUND_COLOR)
        count_type1 = 0
        count_type2 = 0

        for it in items:
            it.move()
            it.draw(render_surface)
            if it.color == LOGIC_COLOR1:
                count_type1 += 1
            else:
                count_type2 += 1

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # --------------------------------------------------
        # Scoreboard (if SHOW_SCOREBOARD)
        # Now each letter is drawn in its color with a white outline
        # --------------------------------------------------
        if SHOW_SCOREBOARD:
            # "J: X"
            text_j = f"{LETTER1}: {count_type1}"
            scoreboard_surf_j = render_text_with_outline(scoreboard_font, text_j, LETTER1_COLOR, (255, 255, 255), 2)

            # "S: Y"
            text_s = f"{LETTER2}: {count_type2}"
            scoreboard_surf_s = render_text_with_outline(scoreboard_font, text_s, LETTER2_COLOR, (255, 255, 255), 2)

            # Blit each scoreboard piece side-by-side with a small gap
            screen.blit(scoreboard_surf_j, (10, 10))
            screen.blit(scoreboard_surf_s, (10 + scoreboard_surf_j.get_width() + 20, 10))

        # Check winner
        if not winner_declared:
            if count_type1 == 0:
                winner_declared = True
                winner_text = f"{LETTER2} WINS!"
            elif count_type2 == 0:
                winner_declared = True
                winner_text = f"{LETTER1} WINS!"

        # Winner overlay (if SHOW_WINNER_OVERLAY)
        if SHOW_WINNER_OVERLAY and winner_declared and winner_text:
            winner_surf = render_text_with_outline(winner_font, winner_text, (255, 255, 255),
                                                   (0, 0, 0), 3)
            wrect = winner_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(winner_surf, wrect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
