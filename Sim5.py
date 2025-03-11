import os
import pygame
import random
import math  # Needed for cos/sin

# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

SCREEN_WIDTH = 432
SCREEN_HEIGHT = 768
RENDER_WIDTH = 1080
RENDER_HEIGHT = 1920
FPS = 60

# TEAM-SPECIFIC SPEEDS
TEAM1_SPEED = 1
TEAM2_SPEED = 5

TEAM1_WALL_RADIUS = 35
TEAM1_COLLISION_RADIUS = 35
TEAM2_WALL_RADIUS = 170
TEAM2_COLLISION_RADIUS = 200

TEAM1_NAME = "Bubbles"
TEAM2_NAME = "Spike"

TEAM1_IMAGE_PATH = "bubble.png"
TEAM2_IMAGE_PATH = "Spike2.png"

TEAM1_IMAGE_SIZE = (75, 75)
TEAM2_IMAGE_SIZE = (400, 400)

TEAM1_COUNT = 200
TEAM2_COUNT = 1

LOGIC_COLOR1 = (255, 69, 0)    # Bubbles
LOGIC_COLOR2 = (0, 255, 255)   # Spikes

TEAM1_TEXT_COLOR = (219, 168, 223)
TEAM2_TEXT_COLOR = (219, 168, 223)

BACKGROUND_COLOR = (0, 0, 0)

SEED = 4
INITIAL_PAUSE_SECONDS = 3

# New variable for simulation duration (timer countdown)
SIMULATION_DURATION_SECONDS = 30

# ------------------------------------------------------------------------
# KEY CHANGE FOR COLLISION: Larger grid size
# ------------------------------------------------------------------------
GRID_SIZE = 400

NEIGHBOR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]

# Show scoreboard for Team 1 and timer in the corners
SHOW_SCOREBOARD = True
SHOW_WINNER_OVERLAY = True
SCOREBOARD_FONT_SIZE = 25

# ------------------------------------------------------------------------
# Sound Config
# ------------------------------------------------------------------------
SOUND_COOLDOWN_MS = 100
SWAP_SOUND_COOLDOWN_MS = 500

last_collision_sound_tick = 0

AMBIENT_VOLUME_PERCENT = 60
COLLISION_VOLUME_PERCENT = 20
SWAP_VOLUME_PERCENT = 140
VICTORY_VOLUME_PERCENT = 80
START_VOLUME_PERCENT = 40

# --- New Sound Options ---
# sound_options: 1 uses the original single collision sound.
# 2 uses cycling pop sounds for each bubble pop.
sound_options = 2  # Change to 1 for original behavior

# Variables used by the original collision song (if needed)
COLLISION_SONG_PATH = "TMOTTBG.mp3"
SOUND_SNIPPET_DURATION = 0.1
SOUND_FADEOUT_MS = 20
COLLISION_SONG_TOTAL_DURATION = 180.0
collision_song_pos = 0.0
COLLISION_SNIPPET_STOP_EVENT = pygame.USEREVENT + 1

# For sound option 2: list of pop sounds and an index to cycle through them.
pop_sound_list = []
current_pop_sound_index = 0

# ------------------------------------------------------------------------
# Pygame Init
# ------------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Team Battle Simulation")
pygame.mixer.init()

ambient_sound = None
collision_sound = None  # used in sound option 1
swap_sound = None
victory_sound = None
start_sound = None

if os.path.exists("ambient.wav"):
    ambient_sound = pygame.mixer.Sound("ambient.wav")
    ambient_sound.set_volume(AMBIENT_VOLUME_PERCENT / 100.0)

if sound_options == 1:
    if os.path.exists("collision7.mp3"):
        collision_sound = pygame.mixer.Sound("collision7.mp3")
        collision_sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
    else:
        print("collision7.mp3 not found!")
elif sound_options == 2:
    # Define your list of pop sound files here.
    pop_sound_files = ["collision7.mp3", "pop2.wav", "pop5.wav"]  # Modify as needed
    for file in pop_sound_files:
        if os.path.exists(file):
            sound = pygame.mixer.Sound(file)
            sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
            pop_sound_list.append(sound)
        else:
            print(f"Pop sound file {file} not found!")
    current_pop_sound_index = 0

if os.path.exists("swap.wav"):
    swap_sound = pygame.mixer.Sound("swap.wav")
    swap_sound.set_volume(SWAP_VOLUME_PERCENT / 100.0)

if os.path.exists("victory.wav"):
    victory_sound = pygame.mixer.Sound("victory.wav")
    victory_sound.set_volume(VICTORY_VOLUME_PERCENT / 100.0)

if os.path.exists("start.wav"):
    start_sound = pygame.mixer.Sound("start.wav")
    start_sound.set_volume(START_VOLUME_PERCENT / 100.0)

# (Removed the pygame.mixer.music loading block from the original SOUND_OPTION==2 branch)

render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

dominant_color = None
submissive_color = None

# ------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------
def clamp_0_255(val: int) -> int:
    """Clamp an integer to the [0..255] range."""
    return max(0, min(255, val))

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
# Load Team Images
# ------------------------------------------------------------------------
if os.path.exists(TEAM1_IMAGE_PATH):
    team1_raw = pygame.image.load(TEAM1_IMAGE_PATH).convert_alpha()
    team1_surf = pygame.transform.scale(team1_raw, TEAM1_IMAGE_SIZE)
else:
    team1_surf = pygame.Surface(TEAM1_IMAGE_SIZE)
    team1_surf.fill((255, 0, 0))

if os.path.exists(TEAM2_IMAGE_PATH):
    team2_raw = pygame.image.load(TEAM2_IMAGE_PATH).convert_alpha()
    team2_surf = pygame.transform.scale(team2_raw, TEAM2_IMAGE_SIZE)
else:
    team2_surf = pygame.Surface(TEAM2_IMAGE_SIZE)
    team2_surf.fill((0, 255, 0))

ITEM_SURF_MAP = {
    LOGIC_COLOR1: team1_surf,  # Bubbles
    LOGIC_COLOR2: team2_surf   # Spikes
}

# ------------------------------------------------------------------------
# PopFragment: droplet-like pieces
# ------------------------------------------------------------------------
class PopFragment:
    """
    Represents a small particle that shoots out from the bubble center.
    It fades out over time.
    """
    def __init__(self, x, y, angle, speed, start_tick, lifespan=800):
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.angle = angle
        self.speed = speed
        self.start_tick = start_tick
        self.lifespan = lifespan
        self.size = random.randint(6, 12)

    def update_and_draw(self, surface, current_tick):
        elapsed = current_tick - self.start_tick
        if elapsed > self.lifespan:
            return False
        frac = elapsed / self.lifespan
        frac = max(0, min(1, frac))
        dist = self.speed * elapsed
        self.x = self.start_x + dist * math.cos(self.angle)
        self.y = self.start_y + dist * math.sin(self.angle)
        alpha = clamp_0_255(int(255 * (1.0 - frac)))
        fragment_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        color = (200, 220, 255, alpha)
        pygame.draw.circle(fragment_surf, color, (self.size, self.size), self.size)
        surface.blit(fragment_surf, (self.x - self.size, self.y - self.size))
        return True

# ------------------------------------------------------------------------
# PopAnimation: bigger ring + fragment droplets
# ------------------------------------------------------------------------
class PopAnimation:
    """
    Creates a ring plus multiple fragment droplets.
    """
    def __init__(self, x, y, start_tick, duration=500):
        self.x = x
        self.y = y
        self.start_tick = start_tick
        self.duration = duration
        self.fragments = []
        num_fragments = random.randint(10, 15)
        for _ in range(num_fragments):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.1, 0.3)
            frag = PopFragment(self.x, self.y, angle, speed, start_tick)
            self.fragments.append(frag)

    def update_and_draw(self, surface, current_tick):
        elapsed = current_tick - self.start_tick
        done = True
        if elapsed <= self.duration:
            progress = max(0, min(1, elapsed / self.duration))
            radius = int(20 + 60 * progress)
            alpha = clamp_0_255(int(255 * (1.0 - progress)))
            ring_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255, 255, 255, alpha), (radius, radius), radius, width=4)
            surface.blit(ring_surf, (self.x - radius, self.y - radius))
            done = False
        new_fragments = []
        for frag in self.fragments:
            if frag.update_and_draw(surface, current_tick):
                new_fragments.append(frag)
        self.fragments = new_fragments
        if self.fragments:
            done = False
        return not done

# ------------------------------------------------------------------------
# Item Class (with separate wall_radius & collision_radius)
# ------------------------------------------------------------------------
class Item:
    __slots__ = (
        'x', 'y',
        'wall_radius',       # used for bouncing off walls
        'collision_radius',  # used for hitting other items
        'color', 'vx', 'vy',
        'last_conversion_time', 'final_x', 'final_y', 'start_y'
    )

    def __init__(self, x, y, wall_radius, collision_radius, color, vx, vy, final_x, final_y, start_y):
        self.x = x
        self.y = y
        self.wall_radius = wall_radius
        self.collision_radius = collision_radius
        self.color = color
        self.vx = vx
        self.vy = vy
        self.last_conversion_time = float('-inf')
        self.final_x = final_x
        self.final_y = final_y
        self.start_y = start_y

    def move(self):
        new_x = self.x + self.vx
        new_y = self.y + self.vy
        r = self.wall_radius  # Bouncing uses wall_radius only
        if new_x - r < 0 or new_x + r > RENDER_WIDTH:
            self.vx = -self.vx
        else:
            self.x = new_x
        if new_y - r < 0 or new_y + r > RENDER_HEIGHT:
            self.vy = -self.vy
        else:
            self.y = new_y

    def draw(self, surface):
        image_surf = ITEM_SURF_MAP[self.color]
        draw_x = int(self.x - image_surf.get_width() / 2)
        draw_y = int(self.y - image_surf.get_height() / 2)
        surface.blit(image_surf, (draw_x, draw_y))
        # Uncomment below to draw a debug collision circle:
        # pygame.draw.circle(surface, (0, 255, 0), (int(self.x), int(self.y)), self.collision_radius, width=2)

    def check_collision(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        distance_sq = dx * dx + dy * dy
        combined_radius = self.collision_radius + other.collision_radius
        return distance_sq < (combined_radius * combined_radius)

    def resolve_collision(self, other, current_time, to_remove, pop_events):
        global last_collision_sound_tick, current_pop_sound_index, pop_sound_list
        is_self_bubble = (self.color == LOGIC_COLOR1)
        is_other_bubble = (other.color == LOGIC_COLOR1)
        is_self_spike = (self.color == LOGIC_COLOR2)
        is_other_spike = (other.color == LOGIC_COLOR2)
        # Bubble collides with Spike => Bubble pops
        if is_self_bubble and is_other_spike:
            to_remove.add(self)
            pop_events.append((self.x, self.y))
            current_tick = pygame.time.get_ticks()
            if sound_options == 1:
                if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    collision_sound.play()
                    last_collision_sound_tick = current_tick
            elif sound_options == 2:
                if pop_sound_list and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    random.choice(pop_sound_list).play()
                    last_collision_sound_tick = current_tick
        elif is_other_bubble and is_self_spike:
            to_remove.add(other)
            pop_events.append((other.x, other.y))
            current_tick = pygame.time.get_ticks()
            if sound_options == 1:
                if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    collision_sound.play()
                    last_collision_sound_tick = current_tick
            elif sound_options == 2:
                if pop_sound_list and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    pop_sound_list[current_pop_sound_index].play()
                    current_pop_sound_index = (current_pop_sound_index + 1) % len(pop_sound_list)
                    last_collision_sound_tick = current_tick

# ------------------------------------------------------------------------
# Create Items
# ------------------------------------------------------------------------
def create_items(count1, count2, seed=None):
    if seed is not None:
        random.seed(seed)
    items = []
    # Bubbles
    for _ in range(count1):
        w_r = TEAM1_WALL_RADIUS
        c_r = TEAM1_COLLISION_RADIUS
        max_x = RENDER_WIDTH - w_r
        max_y = RENDER_HEIGHT - w_r
        final_x = random.randint(w_r, max_x)
        final_y = random.randint(w_r, max_y)
        start_y = random.randint(-1000, -w_r)
        vx = TEAM1_SPEED if random.random() < 0.5 else -TEAM1_SPEED
        vy = TEAM1_SPEED if random.random() < 0.5 else -TEAM1_SPEED
        items.append(Item(
            x=final_x, y=start_y,
            wall_radius=w_r,
            collision_radius=c_r,
            color=LOGIC_COLOR1,
            vx=vx, vy=vy,
            final_x=final_x, final_y=final_y, start_y=start_y
        ))
    # Spikes
    for _ in range(count2):
        w_r = TEAM2_WALL_RADIUS
        c_r = TEAM2_COLLISION_RADIUS
        max_x = RENDER_WIDTH - w_r
        max_y = RENDER_HEIGHT - w_r
        final_x = random.randint(w_r, max_x)
        final_y = random.randint(w_r, max_y)
        start_y = random.randint(-1000, -w_r)
        vx = TEAM2_SPEED if random.random() < 0.5 else -TEAM2_SPEED
        vy = TEAM2_SPEED if random.random() < 0.5 else -TEAM2_SPEED
        items.append(Item(
            x=final_x, y=start_y,
            wall_radius=w_r,
            collision_radius=c_r,
            color=LOGIC_COLOR2,
            vx=vx, vy=vy,
            final_x=final_x, final_y=final_y, start_y=start_y
        ))
    return items

# ------------------------------------------------------------------------
# Spatial Partition
# ------------------------------------------------------------------------
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

# ------------------------------------------------------------------------
# Check Collisions
# ------------------------------------------------------------------------
def check_collisions(grid, current_time, items, explosions):
    to_remove = set()
    pop_events = []
    for (cx, cy), cell_items in grid.items():
        c_len = len(cell_items)
        for i in range(c_len):
            it_i = cell_items[i]
            for j in range(i + 1, c_len):
                it_j = cell_items[j]
                if it_i.check_collision(it_j):
                    it_i.resolve_collision(it_j, current_time, to_remove, pop_events)
        for ox, oy in NEIGHBOR_OFFSETS:
            neighbor = (cx + ox, cy + oy)
            if neighbor in grid:
                neighbor_items = grid[neighbor]
                for it_i in cell_items:
                    for it_j in neighbor_items:
                        if it_i.check_collision(it_j):
                            it_i.resolve_collision(it_j, current_time, to_remove, pop_events)
    if to_remove:
        for dead in to_remove:
            if dead in items:
                items.remove(dead)
    current_tick = pygame.time.get_ticks()
    for (px, py) in pop_events:
        explosions.append(PopAnimation(px, py, current_tick))

def determine_initial_dominance():
    global dominant_color, submissive_color
    if TEAM1_COUNT < TEAM2_COUNT:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2
    elif TEAM2_COUNT < TEAM1_COUNT:
        dominant_color, submissive_color = LOGIC_COLOR2, LOGIC_COLOR1
    else:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2

# ------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------
def main():
    global collision_song_pos
    determine_initial_dominance()
    items = create_items(TEAM1_COUNT, TEAM2_COUNT, seed=SEED)
    clock = pygame.time.Clock()
    scoreboard_font = pygame.font.SysFont(None, SCOREBOARD_FONT_SIZE)
    winner_font = pygame.font.SysFont(None, 72)

    winner_declared = False
    winner_text = ""
    winner_declared_time = None
    victory_sound_played = False

    # For freezing the timer when bubbles are gone (Spike wins)
    freeze_timer = False
    frozen_elapsed_seconds = None

    # 1) Initial Pause
    start_time = pygame.time.get_ticks()
    pause_duration = INITIAL_PAUSE_SECONDS * 1000
    while pygame.time.get_ticks() - start_time < pause_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
        render_surface.fill(BACKGROUND_COLOR)
        for it in items:
            it.draw(render_surface)
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

    # 2) Countdown + falling
    countdown_font = pygame.font.SysFont(None, 100)
    for second in [3, 2, 1]:
        if collision_sound:
            collision_sound.play()
        segment_start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - segment_start_time < 1000:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    return
            segment_elapsed = pygame.time.get_ticks() - segment_start_time
            fraction = segment_elapsed / 1000.0
            chunk_index = 3 - second
            start_frac = chunk_index / 3.0
            end_frac = (chunk_index + 1) / 3.0
            overall_progress = start_frac + (end_frac - start_frac) * fraction
            for it in items:
                it.y = it.start_y + (it.final_y - it.start_y) * overall_progress
            render_surface.fill(BACKGROUND_COLOR)
            for it in items:
                it.draw(render_surface)
            scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
            screen.blit(scaled_surface, (0, 0))
            countdown_surf = countdown_font.render(str(second), True, (255, 255, 255))
            countdown_rect = countdown_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(countdown_surf, countdown_rect)
            pygame.display.flip()
            clock.tick(FPS)

    # 3) Start sound
    if start_sound:
        start_sound.play()

    # 4) Ambient sound
    if sound_options == 1 and ambient_sound:
        ambient_sound.play(loops=-1)

    # Set simulation start time for the timer
    simulation_start = pygame.time.get_ticks()
    running = True
    explosions = []

    while running:
        current_ticks = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == COLLISION_SNIPPET_STOP_EVENT:
                pygame.mixer.music.fadeout(SOUND_FADEOUT_MS)
                pygame.time.set_timer(COLLISION_SNIPPET_STOP_EVENT, 0)
                collision_song_pos += SOUND_SNIPPET_DURATION
                if collision_song_pos >= COLLISION_SONG_TOTAL_DURATION:
                    collision_song_pos = 0.0

        grid = spatial_partitioning(items)
        check_collisions(grid, current_ticks, items, explosions)

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

        new_explosions = []
        for ex in explosions:
            if ex.update_and_draw(render_surface, current_ticks):
                new_explosions.append(ex)
        explosions = new_explosions

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Timer calculations: freeze the timer if bubbles are gone (Spike wins)
        if freeze_timer:
            elapsed_seconds = frozen_elapsed_seconds
        else:
            elapsed_seconds = (current_ticks - simulation_start) / 1000.0
        time_left = SIMULATION_DURATION_SECONDS - elapsed_seconds
        if time_left < 0:
            time_left = 0

        # When time runs out, if the spike is still active, pop it and declare Bubbles win.
        if time_left <= 0 and not winner_declared:
            for it in items[:]:
                if it.color == LOGIC_COLOR2:
                    explosions.append(PopAnimation(it.x, it.y, current_ticks))
                    if collision_sound:
                        collision_sound.play()
                    items.remove(it)
            winner_declared = True
            winner_text = f"{TEAM1_NAME} WINS!"
            winner_declared_time = current_ticks

        # Winner logic from collisions (if bubbles or spike count reaches 0)
        if not winner_declared:
            if count_type1 == 0:
                winner_declared = True
                winner_text = f"{TEAM2_NAME} WINS!"
                winner_declared_time = current_ticks
                # Freeze the timer when bubbles are all gone (spike wins)
                freeze_timer = True
                frozen_elapsed_seconds = (current_ticks - simulation_start) / 1000.0
            elif count_type2 == 0:
                winner_declared = True
                winner_text = f"{TEAM1_NAME} WINS!"
                winner_declared_time = current_ticks

        # Draw scoreboard: bubble count on top left, timer on top right.
        if SHOW_SCOREBOARD:
            # Bubble count (top left)
            bubble_text = f"{TEAM1_NAME}: {count_type1}"
            bubble_surf = render_text_with_outline(scoreboard_font, bubble_text, TEAM1_TEXT_COLOR, (255, 255, 255), 2)
            screen.blit(bubble_surf, (25, 25))
            
            # Timer (top right) with color based on remaining time.
            if time_left > (2/3 * SIMULATION_DURATION_SECONDS):
                timer_color = (0, 255, 0)
            elif time_left > 10:
                timer_color = (255, 215, 0)
            else:
                timer_color = (255, 0, 0)
            timer_text = f"{time_left:05.2f}"
            timer_surf = render_text_with_outline(scoreboard_font, timer_text, timer_color, (255, 255, 255), 2)
            timer_x = SCREEN_WIDTH - timer_surf.get_width() - 25
            screen.blit(timer_surf, (timer_x, 25))

        # Winner overlay (only show if 1 second has passed since win condition)
        if SHOW_WINNER_OVERLAY and winner_declared and winner_text and winner_declared_time is not None:
            if current_ticks - winner_declared_time >= 1000:
                if not victory_sound_played and victory_sound:
                    victory_sound.play()
                    victory_sound_played = True
                winner_surf = render_text_with_outline(winner_font, winner_text, (255, 255, 255), (0, 0, 0), 3)
                wrect = winner_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                screen.blit(winner_surf, wrect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
