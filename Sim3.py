import os
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
PARTICLE_RADIUS = 50

# Movement speed
PARTICLE_SPEED = 0.82

# ------------------------------------------------------------------------
# New: Team Names, Image Paths, and Image Sizes
# ------------------------------------------------------------------------
TEAM1_NAME = "Baseball"
TEAM2_NAME = "Soccer"

TEAM1_IMAGE_PATH = "baseball3.png"  # Replace with your PNG file
TEAM2_IMAGE_PATH = "soccer3.png"  # Replace with your PNG file

# Easy way to change image sizes (width,height)
TEAM1_IMAGE_SIZE = (100, 100)
TEAM2_IMAGE_SIZE = (100, 100)

# ------------------------------------------------------------------------
# Initial counts for each team
# ------------------------------------------------------------------------
TEAM1_COUNT = 100
TEAM2_COUNT = 100

# Threshold-based phase switching (unchanged)
LAST_NUM_PARTICLES = 37
MIDDLE_LAST_NUM_PARTICLES = 52
MIDDLE_GROUP = 8
SECOND_LAST_NUM_PARTICLES = 15
SECOND_LAST_GROUP = 14
FINAL_LAST_NUM_PARTICLES = 0
FINAL_LAST_GROUP = 22

# These are purely for dominance/collision logic (not drawn as colors)
LOGIC_COLOR1 = (255, 69, 0)   # For Team1 in logic
LOGIC_COLOR2 = (0, 255, 255)  # For Team2 in logic

# ------------------------------------------------------------------------
# Colors used for scoreboard text, same as old LETTER1_COLOR / LETTER2_COLOR
# ------------------------------------------------------------------------
TEAM1_TEXT_COLOR = (83,12,14)   # First color (Red)
TEAM2_TEXT_COLOR = (9,46,6)  # second color (Green)

BACKGROUND_COLOR = (0, 0, 0)

SEED = 5
CONVERSION_COOLDOWN = 0.065
INITIAL_PAUSE_SECONDS = 3  # This is our separate initial pause
GRID_SIZE = 50

NEIGHBOR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]

# Toggles
SHOW_SCOREBOARD = True
SHOW_WINNER_OVERLAY = True
SHOW_PREDICTION_TEXT = True

# Fonts
SCOREBOARD_FONT_SIZE = 30
PREDICTION_FONT_SIZE = 40

# ------------------------------------------------------------------------
# Additional Sound Cooldowns & Timestamps
# ------------------------------------------------------------------------
SOUND_COOLDOWN_MS = 100      # Minimum time (ms) between collision sounds
SWAP_SOUND_COOLDOWN_MS = 500 # Minimum time (ms) between swap sounds

last_collision_sound_tick = 0
last_swap_sound_tick = 0

# ------------------------------------------------------------------------
# Sound Volume Configuration (Percentage)
# ------------------------------------------------------------------------
AMBIENT_VOLUME_PERCENT = 240
COLLISION_VOLUME_PERCENT = 11
SWAP_VOLUME_PERCENT = 140
VICTORY_VOLUME_PERCENT = 80
START_VOLUME_PERCENT = 40  # Volume for the "start.wav" if you want to adjust it

# ------------------------------------------------------------------------
# NEW: Sound Design Option Settings
# ------------------------------------------------------------------------
# SOUND_OPTION: set to 1 for current design, set to 2 for new collision-song design
SOUND_OPTION = 1

# For Option 2: collision song based design (only active when SOUND_OPTION == 2)
COLLISION_SONG_PATH = "TMOTTBG.mp3"  # Change as needed
SOUND_SNIPPET_DURATION = 0.1   # Duration (in seconds) of each snippet played per collision
SOUND_FADEOUT_MS = 20          # Fade-out duration in ms to smooth stopping
COLLISION_SONG_TOTAL_DURATION = 180.0  # Total duration (in seconds) of the collision song (adjust as needed)
collision_song_pos = 0.0       # Global tracker for current playback position
COLLISION_SNIPPET_STOP_EVENT = pygame.USEREVENT + 1  # Custom event to stop snippet playback

# ------------------------------------------------------------------------
# Pygame Initialization and Sound Loading
# ------------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Team Battle Simulation")

pygame.mixer.init()

ambient_sound = None
collision_sound = None
swap_sound = None
victory_sound = None
start_sound = None  # New start sound

if os.path.exists("ambient.wav"):
    ambient_sound = pygame.mixer.Sound("ambient.wav")
    ambient_sound.set_volume(AMBIENT_VOLUME_PERCENT / 100.0)

if os.path.exists("collision7.mp3"):
    collision_sound = pygame.mixer.Sound("collision7.mp3")
    collision_sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)

if os.path.exists("swap.wav"):
    swap_sound = pygame.mixer.Sound("swap.wav")
    swap_sound.set_volume(SWAP_VOLUME_PERCENT / 100.0)

if os.path.exists("victory.wav"):
    victory_sound = pygame.mixer.Sound("victory.wav")
    victory_sound.set_volume(VICTORY_VOLUME_PERCENT / 100.0)

# (New) Load the start sound if present
if os.path.exists("start.wav"):
    start_sound = pygame.mixer.Sound("start.wav")
    start_sound.set_volume(START_VOLUME_PERCENT / 100.0)

# For SOUND_OPTION 2, load the collision song via pygame.mixer.music
if SOUND_OPTION == 2:
    if os.path.exists(COLLISION_SONG_PATH):
        pygame.mixer.music.load(COLLISION_SONG_PATH)
    else:
        print("Collision song file not found!")

# High-resolution render surface
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

# Internal logic for dominance
dominant_color = None  # will be either LOGIC_COLOR1 or LOGIC_COLOR2
submissive_color = None  # likewise

# ------------------------------------------------------------------------
# Function to render text with a simple white outline (stroke)
# ------------------------------------------------------------------------
def render_text_with_outline(font, text, text_color, outline_color=(255, 255, 255), outline_width=2):
    base_surface = font.render(text, True, text_color)
    width, height = base_surface.get_size()

    outline_surface = pygame.Surface((width + 2 * outline_width, height + 2 * outline_width), pygame.SRCALPHA)
    
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            outline_surface.blit(
                font.render(text, True, outline_color),
                (dx + outline_width, dy + outline_width)
            )

    outline_surface.blit(base_surface, (outline_width, outline_width))
    return outline_surface

# ------------------------------------------------------------------------
# New: Load two PNG surfaces for each team, scaled to the desired size
# ------------------------------------------------------------------------
if os.path.exists(TEAM1_IMAGE_PATH):
    team1_raw = pygame.image.load(TEAM1_IMAGE_PATH).convert_alpha()
    team1_surf = pygame.transform.scale(team1_raw, TEAM1_IMAGE_SIZE)
else:
    # Fallback: if the image doesn't exist, just fill a rect
    team1_surf = pygame.Surface(TEAM1_IMAGE_SIZE)
    team1_surf.fill((255, 0, 0))

if os.path.exists(TEAM2_IMAGE_PATH):
    team2_raw = pygame.image.load(TEAM2_IMAGE_PATH).convert_alpha()
    team2_surf = pygame.transform.scale(team2_raw, TEAM2_IMAGE_SIZE)
else:
    # Fallback: if the image doesn't exist, just fill a rect
    team2_surf = pygame.Surface(TEAM2_IMAGE_SIZE)
    team2_surf.fill((0, 255, 0))

# Map each logic color to the appropriate team surface
ITEM_SURF_MAP = {
    LOGIC_COLOR1: team1_surf,
    LOGIC_COLOR2: team2_surf
}

# ------------------------------------------------------------------------
# Item class (unchanged except for drawing images instead of letters)
# ------------------------------------------------------------------------
class Item:
    """
    Modified to include final_x, final_y, and start_y
    so we can do the falling animation in the countdown.
    """
    __slots__ = ('x', 'y', 'radius', 'color', 'vx', 'vy',
                 'last_conversion_time', 'final_x', 'final_y', 'start_y')

    def __init__(self, x, y, radius, color, vx, vy, final_x, final_y, start_y):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color  # LOGIC_COLOR1 or LOGIC_COLOR2
        self.vx = vx
        self.vy = vy
        self.last_conversion_time = float('-inf')
        # For the falling animation
        self.final_x = final_x
        self.final_y = final_y
        self.start_y = start_y

    def move(self):
        new_x = self.x + self.vx
        new_y = self.y + self.vy
        r = self.radius

        if new_x - r < 0 or new_x + r > RENDER_WIDTH:
            self.vx = -self.vx
        else:
            self.x = new_x

        if new_y - r < 0 or new_y + r > RENDER_HEIGHT:
            self.vy = -self.vy
        else:
            self.y = new_y

    def draw(self, surface):
        # Draw using the PNG surface based on self.color
        image_surf = ITEM_SURF_MAP[self.color]
        # Compute the top-left for blitting, so that the image is centered
        draw_x = int(self.x - image_surf.get_width() / 2)
        draw_y = int(self.y - image_surf.get_height() / 2)
        surface.blit(image_surf, (draw_x, draw_y))

    def check_collision(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        distance_sq = dx * dx + dy * dy
        combined_radius = self.radius + other.radius
        return distance_sq < (combined_radius * combined_radius)

    def resolve_collision(self, other, current_time):
        global dominant_color, submissive_color, last_collision_sound_tick, collision_song_pos
        # Conversion if I'm dominant and the other is submissive
        if self.color == dominant_color and other.color == submissive_color:
            if (current_time - self.last_conversion_time) >= CONVERSION_COOLDOWN:
                other.color = dominant_color
                other.last_conversion_time = current_time
                self.last_conversion_time = current_time

                # Sound design changes: play collision snippet based on chosen option
                current_tick = pygame.time.get_ticks()
                if SOUND_OPTION == 1:
                    if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                        collision_sound.play()
                        last_collision_sound_tick = current_tick
                elif SOUND_OPTION == 2:
                    if current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS and not pygame.mixer.music.get_busy():
                        pygame.mixer.music.play(loops=0, start=collision_song_pos, fade_ms=20)
                        last_collision_sound_tick = current_tick
                        pygame.time.set_timer(COLLISION_SNIPPET_STOP_EVENT, int(SOUND_SNIPPET_DURATION * 1000))
        # Conversion if the other is dominant and I'm submissive
        elif other.color == dominant_color and self.color == submissive_color:
            if (current_time - other.last_conversion_time) >= CONVERSION_COOLDOWN:
                self.color = dominant_color
                self.last_conversion_time = current_time
                other.last_conversion_time = current_time

                # Sound design changes: play collision snippet based on chosen option
                current_tick = pygame.time.get_ticks()
                if SOUND_OPTION == 1:
                    if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                        collision_sound.play()
                        last_collision_sound_tick = current_tick
                elif SOUND_OPTION == 2:
                    if current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS and not pygame.mixer.music.get_busy():
                        pygame.mixer.music.play(loops=0, start=collision_song_pos, fade_ms=20)
                        last_collision_sound_tick = current_tick
                        pygame.time.set_timer(COLLISION_SNIPPET_STOP_EVENT, int(SOUND_SNIPPET_DURATION * 1000))

# ------------------------------------------------------------------------
# Create items for both teams
# ------------------------------------------------------------------------
def create_items(count1, count2, speed, seed=None):
    """
    Modified to store final_x, final_y, and a random negative start_y
    so each Item can 'fall' during the countdown.
    """
    if seed is not None:
        random.seed(seed)

    items = []
    r = PARTICLE_RADIUS
    max_x = RENDER_WIDTH - r
    max_y = RENDER_HEIGHT - r

    # Team1 items
    for _ in range(count1):
        final_x = random.randint(r, max_x)
        final_y = random.randint(r, max_y)
        start_y = random.randint(-1000, -r)  # start above the screen
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        items.append(Item(final_x, start_y, r, LOGIC_COLOR1, vx, vy,
                          final_x, final_y, start_y))

    # Team2 items
    for _ in range(count2):
        final_x = random.randint(r, max_x)
        final_y = random.randint(r, max_y)
        start_y = random.randint(-1000, -r)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        items.append(Item(final_x, start_y, r, LOGIC_COLOR2, vx, vy,
                          final_x, final_y, start_y))

    return items

def spatial_partitioning(items):
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
    On swap, play 'swap.wav' if present, with a cooldown.
    """
    global dominant_color, submissive_color
    global last_swap_sound_tick

    previous_dominant = dominant_color

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

    if previous_dominant != dominant_color:
        current_tick = pygame.time.get_ticks()
        if swap_sound and current_tick - last_swap_sound_tick > SWAP_SOUND_COOLDOWN_MS:
            swap_sound.play()
            last_swap_sound_tick = current_tick

def determine_initial_dominance():
    global dominant_color, submissive_color
    if TEAM1_COUNT < TEAM2_COUNT:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2
    elif TEAM2_COUNT < TEAM1_COUNT:
        dominant_color, submissive_color = LOGIC_COLOR2, LOGIC_COLOR1
    else:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2

# Helper function: Draw text with outline
def draw_text_with_border(surface, text, font, text_color, border_color, pos, border_width=2):
    for dx in [-border_width, 0, border_width]:
        for dy in [-border_width, 0, border_width]:
            if dx != 0 or dy != 0:
                border_surface = font.render(text, True, border_color)
                surface.blit(border_surface, (pos[0] + dx, pos[1] + dy))
    text_surface = font.render(text, True, text_color)
    surface.blit(text_surface, pos)

def main():
    global dominant_color, submissive_color, collision_song_pos  # needed for option 2 updates

    determine_initial_dominance()
    items = create_items(TEAM1_COUNT, TEAM2_COUNT, PARTICLE_SPEED, seed=SEED)
    clock = pygame.time.Clock()

    # Fonts for scoreboard & winner overlay
    scoreboard_font = pygame.font.SysFont(None, SCOREBOARD_FONT_SIZE)
    winner_font = pygame.font.SysFont(None, 72)
    prediction_font = pygame.font.SysFont(None, PREDICTION_FONT_SIZE)

    winner_declared = False
    winner_text = ""

    # --------------------------
    # 1) Initial Pause
    # --------------------------
    start_time = pygame.time.get_ticks()
    pause_duration = INITIAL_PAUSE_SECONDS * 1000
    while pygame.time.get_ticks() - start_time < pause_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return

        render_surface.fill(BACKGROUND_COLOR)
        for it in items:
            # Just draw them at their starting position (above screen)
            it.draw(render_surface)

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

    # --------------------------
    # 2) 3-SECOND COUNTDOWN + FALLING ANIMATION
    # --------------------------
    countdown_font = pygame.font.SysFont(None, 100)

    for second in [3, 2, 1]:
        # Optional beep at the start of each 1-second segment
        if collision_sound:
            collision_sound.play()

        segment_start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - segment_start_time < 1000:  # one-second chunk
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    return

            # Fraction for this 1-second chunk (0 to 1)
            segment_elapsed = pygame.time.get_ticks() - segment_start_time
            fraction = segment_elapsed / 1000.0

            # We figure out the overall fraction of the 3-second fall
            chunk_index = 3 - second  # 0,1,2 for second=3,2,1
            start_frac = chunk_index / 3.0
            end_frac = (chunk_index + 1) / 3.0
            overall_progress = start_frac + (end_frac - start_frac) * fraction

            # Update each item's y position to reflect partial fall
            for it in items:
                it.y = it.start_y + (it.final_y - it.start_y) * overall_progress

            render_surface.fill(BACKGROUND_COLOR)
            for it in items:
                it.draw(render_surface)

            scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
            screen.blit(scaled_surface, (0, 0))

            # Show the big countdown number
            countdown_surf = countdown_font.render(str(second), True, (255, 255, 255))
            countdown_rect = countdown_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(countdown_surf, countdown_rect)

            pygame.display.flip()
            clock.tick(FPS)

    # --------------------------
    # 3) After countdown, play a start sound if available
    # --------------------------
    if start_sound:
        start_sound.play()

    # --------------------------
    # 4) Start ambient loop & normal simulation
    # --------------------------
    # Only play ambient sound in SOUND_OPTION 1 (current design)
    if SOUND_OPTION == 1 and ambient_sound:
        ambient_sound.play(loops=-1)

    simulation_start = pygame.time.get_ticks()
    running = True
    while running:
        current_ticks = pygame.time.get_ticks()
        elapsed_time = (current_ticks - simulation_start) / 1000.0

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            # Handle collision snippet stop event for SOUND_OPTION 2
            elif event.type == COLLISION_SNIPPET_STOP_EVENT:
                pygame.mixer.music.fadeout(SOUND_FADEOUT_MS)
                pygame.time.set_timer(COLLISION_SNIPPET_STOP_EVENT, 0)
                collision_song_pos += SOUND_SNIPPET_DURATION
                if collision_song_pos >= COLLISION_SONG_TOTAL_DURATION:
                    collision_song_pos = 0.0

        # Time-based dominance logic
        check_last_items(items, elapsed_time)

        # Collisions
        grid = spatial_partitioning(items)
        check_collisions(grid, elapsed_time)

        # Drawing
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
        # Scoreboard (displays team names & counts)
        # --------------------------------------------------
        if SHOW_SCOREBOARD:
            # Left scoreboard (Team1)
            text_left = f"{TEAM1_NAME}: {count_type1}"
            scoreboard_surf_left = render_text_with_outline(
                scoreboard_font, text_left, TEAM1_TEXT_COLOR, (255, 255, 255), 2
            )
            screen.blit(scoreboard_surf_left, (23, 23))

            # Right scoreboard (Team2)
            text_right = f"{TEAM2_NAME}: {count_type2}"
            scoreboard_surf_right = render_text_with_outline(
                scoreboard_font, text_right, TEAM2_TEXT_COLOR, (255, 255, 255), 2)
            right_width = scoreboard_surf_right.get_width()
            screen.blit(scoreboard_surf_right, (SCREEN_WIDTH - right_width - 23, 23))

        # Draw the prediction text if enabled and no winner yet.
        if SHOW_PREDICTION_TEXT and not winner_declared:
            prediction_text = "what sport will win?"
            # Position: centered horizontally, a bit lower than the scoreboard (e.g. below the left/right texts)
            prediction_y = 23 + scoreboard_font.get_height() + 22
            pred_text_surface = prediction_font.render(prediction_text, True, (0,0,0))
            pred_text_rect = pred_text_surface.get_rect(center=(SCREEN_WIDTH//2, prediction_y))
            draw_text_with_border(screen, prediction_text, prediction_font, (0,0,0), (255,255,255), pred_text_rect.topleft)

        # Winner check
        if not winner_declared:
            if count_type1 == 0:
                winner_declared = True
                winner_text = f"{TEAM2_NAME} WINS!"
                if victory_sound:
                    victory_sound.play()
            elif count_type2 == 0:
                winner_declared = True
                winner_text = f"{TEAM1_NAME} WINS!"
                if victory_sound:
                    victory_sound.play()

        # Winner overlay
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
