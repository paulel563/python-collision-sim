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

# TEAM-SPECIFIC SPEEDS for spikes remain the same
TEAM2_SPEED = 6

TEAM2_WALL_RADIUS = 170
TEAM2_COLLISION_RADIUS = 200

TEAM2_NAME = "Spike"

TEAM2_IMAGE_PATH = "Spike2.png"
TEAM2_IMAGE_SIZE = (400, 400)

TEAM2_COUNT = 1  # Number of spikes

# Logic colors (bubbles and spikes share their own colors)
LOGIC_COLOR1 = (255, 69, 0)    # Bubbles (both groups share this)
LOGIC_COLOR2 = (0, 255, 255)   # Spikes

TEAM1_TEXT_COLOR = (189, 138, 193)
TEAM2_TEXT_COLOR = (189, 138, 193)

BACKGROUND_COLOR = (0, 0, 0)

SEED = 24               # 11, 12 and 20 for 25sec bubble W
INITIAL_PAUSE_SECONDS = 3

# New variable for simulation duration (timer countdown)
SIMULATION_DURATION_SECONDS = 20

# New timer font sizes for dynamic scaling
TIMER_FONT_SIZE_START = 30
TIMER_FONT_SIZE_END = 52

# New configuration for prompt text (always on after the initial pause)
SHOW_PROMPT_TEXT = True
# The prompt text will be constructed dynamically in the main loop.
PROMPT_FONT_SIZE = 30
# PROMPT_COLOR is used for the static text parts (black) while numbers will use TEAM1_TEXT_COLOR.
PROMPT_COLOR = (0, 0, 0)

# ------------------------------------------------------------------------
# Bubble Group Settings
# ------------------------------------------------------------------------
# Both groups share the same logic color (LOGIC_COLOR1) so they contribute to the same counter.
# Each group now defines its own count, wall/collision radius, speed, image, and pop sound list.
SMALL_BUBBLE_SETTINGS = {
    "count": 140,
    "wall_radius": 35,
    "collision_radius": 35,
    "speed": 1,
    "image_path": "bubble.png",
    "image_size": (75, 75),
    "pop_sound_files": ["pop2.wav"]
}

BIG_BUBBLE_SETTINGS = {
    "count": 60,
    "wall_radius": 50,
    "collision_radius": 50,
    "speed": 0.5,
    "image_path": "bubble.png",  # If not found, will fall back to a plain surface
    "image_size": (100, 100),
    "pop_sound_files": ["collision7.mp3"]
}

# ------------------------------------------------------------------------
# KEY CHANGE FOR COLLISION: Larger grid size
# ------------------------------------------------------------------------
GRID_SIZE = 400

NEIGHBOR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]

# Show scoreboard for bubble count and timer in the corners
SHOW_SCOREBOARD = True
SHOW_WINNER_OVERLAY = True
SCOREBOARD_FONT_SIZE = 37

# ------------------------------------------------------------------------
# Sound Config
# ------------------------------------------------------------------------
SOUND_COOLDOWN_MS = 72
SWAP_SOUND_COOLDOWN_MS = 500

last_collision_sound_tick = 0

AMBIENT_VOLUME_PERCENT = 30
COLLISION_VOLUME_PERCENT = 20
SWAP_VOLUME_PERCENT = 140
VICTORY_VOLUME_PERCENT = 80
START_VOLUME_PERCENT = 40

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Team Battle Simulation")
pygame.mixer.init()

# --- New Sound Options ---
# sound_options: 1 uses the original single collision sound.
# 2 uses pop sounds (now per bubble group) for each bubble pop.
sound_options = 2  # Change to 1 for original behavior

ambient_on = True

# Variables used by the original collision song (if needed)
COLLISION_SONG_PATH = "TMOTTBG.mp3"
SOUND_SNIPPET_DURATION = 0.1
SOUND_FADEOUT_MS = 20
COLLISION_SONG_TOTAL_DURATION = 180.0
collision_song_pos = 0.0
COLLISION_SNIPPET_STOP_EVENT = pygame.USEREVENT + 1

# Load countdown sound (always uses collision7.mp3)
if os.path.exists("collision7.mp3"):
    countdown_sound = pygame.mixer.Sound("collision7.mp3")
    countdown_sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
else:
    countdown_sound = None

# For sound option 1 (single collision sound)
collision_sound = None
if sound_options == 1:
    if os.path.exists("collision7.mp3"):
        collision_sound = pygame.mixer.Sound("collision7.mp3")
        collision_sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
    else:
        print("collision7.mp3 not found!")

# For sound option 2: load pop sound lists for each bubble group.
small_bubble_pop_sound_list = []
big_bubble_pop_sound_list = []
if sound_options == 2:
    for file in SMALL_BUBBLE_SETTINGS["pop_sound_files"]:
        if os.path.exists(file):
            sound = pygame.mixer.Sound(file)
            sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
            small_bubble_pop_sound_list.append(sound)
        else:
            print(f"Small bubble pop sound file {file} not found!")
    for file in BIG_BUBBLE_SETTINGS["pop_sound_files"]:
        if os.path.exists(file):
            sound = pygame.mixer.Sound(file)
            sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
            big_bubble_pop_sound_list.append(sound)
        else:
            print(f"Big bubble pop sound file {file} not found!")

if os.path.exists("ambient.wav"):
     ambient_sound = pygame.mixer.Sound("ambient.wav")
     ambient_sound.set_volume(AMBIENT_VOLUME_PERCENT / 100.0)

if os.path.exists("swap.wav"):
    swap_sound = pygame.mixer.Sound("swap.wav")
    swap_sound.set_volume(SWAP_VOLUME_PERCENT / 100.0)
else:
    swap_sound = None

if os.path.exists("victory.wav"):
    victory_sound = pygame.mixer.Sound("victory.wav")
    victory_sound.set_volume(VICTORY_VOLUME_PERCENT / 100.0)
else:
    victory_sound = None

if os.path.exists("start.wav"):
    start_sound = pygame.mixer.Sound("start.wav")
    start_sound.set_volume(START_VOLUME_PERCENT / 100.0)
else:
    start_sound = None

# Spike pop sound for when the spike is popped (always plays), default to pop5.wav.
spike_pop_sound_file = "collision7.mp3"
if os.path.exists(spike_pop_sound_file):
    spike_pop_sound = pygame.mixer.Sound(spike_pop_sound_file)
    spike_pop_sound.set_volume(COLLISION_VOLUME_PERCENT / 100.0)
else:
    spike_pop_sound = None

# (Removed the pygame.mixer.music loading block from the original SOUND_OPTION==2 branch)

render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

# ------------------------------------------------------------------------
# Load Team Images
# ------------------------------------------------------------------------
# For spikes (Team2), we load as before.
if os.path.exists(TEAM2_IMAGE_PATH):
    team2_raw = pygame.image.load(TEAM2_IMAGE_PATH).convert_alpha()
    team2_surf = pygame.transform.scale(team2_raw, TEAM2_IMAGE_SIZE)
else:
    team2_surf = pygame.Surface(TEAM2_IMAGE_SIZE)
    team2_surf.fill((0, 255, 0))

# For bubbles, we load two images (one for small and one for big)
if os.path.exists(SMALL_BUBBLE_SETTINGS["image_path"]):
    small_bubble_raw = pygame.image.load(SMALL_BUBBLE_SETTINGS["image_path"]).convert_alpha()
    small_bubble_surf = pygame.transform.scale(small_bubble_raw, SMALL_BUBBLE_SETTINGS["image_size"])
else:
    small_bubble_surf = pygame.Surface(SMALL_BUBBLE_SETTINGS["image_size"])
    small_bubble_surf.fill((255, 0, 0))

if os.path.exists(BIG_BUBBLE_SETTINGS["image_path"]):
    big_bubble_raw = pygame.image.load(BIG_BUBBLE_SETTINGS["image_path"]).convert_alpha()
    big_bubble_surf = pygame.transform.scale(big_bubble_raw, BIG_BUBBLE_SETTINGS["image_size"])
else:
    big_bubble_surf = pygame.Surface(BIG_BUBBLE_SETTINGS["image_size"])
    big_bubble_surf.fill((255, 0, 0))

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
# Item Class (with separate wall_radius & collision_radius)
# Now includes an image_surf and a pop_sound_list attribute.
# ------------------------------------------------------------------------
class Item:
    __slots__ = (
        'x', 'y',
        'wall_radius',       # used for bouncing off walls
        'collision_radius',  # used for hitting other items
        'color', 'vx', 'vy',
        'last_conversion_time', 'final_x', 'final_y', 'start_y',
        'image_surf', 'pop_sound_list'
    )

    def __init__(self, x, y, wall_radius, collision_radius, color, vx, vy, final_x, final_y, start_y, image_surf, pop_sound_list=None):
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
        self.image_surf = image_surf
        self.pop_sound_list = pop_sound_list

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
        draw_x = int(self.x - self.image_surf.get_width() / 2)
        draw_y = int(self.y - self.image_surf.get_height() / 2)
        surface.blit(self.image_surf, (draw_x, draw_y))
        # Uncomment below to draw a debug collision circle:
        # pygame.draw.circle(surface, (0, 255, 0), (int(self.x), int(self.y)), self.collision_radius, width=2)

    def check_collision(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        distance_sq = dx * dx + dy * dy
        combined_radius = self.collision_radius + other.collision_radius
        return distance_sq < (combined_radius * combined_radius)

    def resolve_collision(self, other, current_time, to_remove, pop_events):
        global last_collision_sound_tick
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
                if self.pop_sound_list and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    random.choice(self.pop_sound_list).play()
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
                if other.pop_sound_list and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    random.choice(other.pop_sound_list).play()
                    last_collision_sound_tick = current_tick

# ------------------------------------------------------------------------
# Create Items
# ------------------------------------------------------------------------
def create_items(seed=None):
    if seed is not None:
        random.seed(seed)
    items = []
    # Create bubbles from both groups
    # Both groups use the same logic color (LOGIC_COLOR1)
    for group, image_surf, group_pop_list in [
        (SMALL_BUBBLE_SETTINGS, small_bubble_surf, small_bubble_pop_sound_list),
        (BIG_BUBBLE_SETTINGS, big_bubble_surf, big_bubble_pop_sound_list)
    ]:
        for _ in range(group["count"]):
            r = group["wall_radius"]
            c_r = group["collision_radius"]
            max_x = RENDER_WIDTH - r
            max_y = RENDER_HEIGHT - r
            final_x = random.randint(r, max_x)
            final_y = random.randint(r, max_y)
            start_y = random.randint(-1000, -r)
            speed = group["speed"]
            vx = speed if random.random() < 0.5 else -speed
            vy = speed if random.random() < 0.5 else -speed
            items.append(Item(
                x=final_x, y=start_y,
                wall_radius=r,
                collision_radius=c_r,
                color=LOGIC_COLOR1,
                vx=vx, vy=vy,
                final_x=final_x, final_y=final_y, start_y=start_y,
                image_surf=image_surf,
                pop_sound_list=group_pop_list if sound_options == 2 else None
            ))
    # Create spikes (Team2) as before
    for _ in range(TEAM2_COUNT):
        r = TEAM2_WALL_RADIUS
        c_r = TEAM2_COLLISION_RADIUS
        max_x = RENDER_WIDTH - r
        max_y = RENDER_HEIGHT - r
        final_x = random.randint(r, max_x)
        final_y = random.randint(r, max_y)
        start_y = random.randint(-1000, -r)
        vx = TEAM2_SPEED if random.random() < 0.5 else -TEAM2_SPEED
        vy = TEAM2_SPEED if random.random() < 0.5 else -TEAM2_SPEED
        items.append(Item(
            x=final_x, y=start_y,
            wall_radius=r,
            collision_radius=c_r,
            color=LOGIC_COLOR2,
            vx=vx, vy=vy,
            final_x=final_x, final_y=final_y, start_y=start_y,
            image_surf=team2_surf,
            pop_sound_list=None
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
    # With two bubble groups, total bubble count is the sum from both groups.
    # Dominance is determined only by comparing bubbles vs spikes.
    global dominant_color, submissive_color
    # For simplicity, if there is at least one bubble, bubbles are dominant.
    if TEAM2_COUNT > 0:
        dominant_color, submissive_color = LOGIC_COLOR1, LOGIC_COLOR2
    else:
        dominant_color, submissive_color = LOGIC_COLOR2, LOGIC_COLOR1

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
# Main
# ------------------------------------------------------------------------
def main():
    determine_initial_dominance()
    items = create_items(seed=SEED)
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

    # 2) Countdown + falling (using countdown_sound always)
    countdown_font = pygame.font.SysFont(None, 100)
    for second in [3, 2, 1]:
        if countdown_sound:
            countdown_sound.play()
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

    # 4) Ambient sound (only for sound option 1)
    if (sound_options == 1) or (ambient_on):
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
                    if spike_pop_sound:
                        spike_pop_sound.play()
                    items.remove(it)
            winner_declared = True
            winner_text = f"{'Bubbles'} WIN!"
            winner_declared_time = current_ticks

        # Winner logic from collisions (if bubbles or spike count reaches 0)
        if not winner_declared:
            if count_type1 == 0:
                winner_declared = True
                winner_text = f"{TEAM2_NAME} WINS!"
                winner_declared_time = current_ticks
                freeze_timer = True
                frozen_elapsed_seconds = (current_ticks - simulation_start) / 1000.0
            elif count_type2 == 0:
                winner_declared = True
                winner_text = f"{'Bubbles'} WIN!"
                winner_declared_time = current_ticks

        # --- New Prompt & Timer Drawing ---
        # Construct the prompt: "Will [bubble count] Bubbles Survive the Spiky Ball?"
        part1 = "Will "
        part2 = f"{count_type1}"
        part3 = " Bubbles Survive the Spiky Ball?"
        part4 = " Bubble Survive the Spiky Ball?"
        prompt_font = pygame.font.SysFont(None, PROMPT_FONT_SIZE)
        surf1 = render_text_with_outline(prompt_font, part1, PROMPT_COLOR, (255, 255, 255), 2)
        surf2 = render_text_with_outline(prompt_font, part2, TEAM1_TEXT_COLOR, (255, 255, 255), 2)
        if count_type1 != 1:
            surf3 = render_text_with_outline(prompt_font, part3, PROMPT_COLOR, (255, 255, 255), 2)
        else:
            surf3 = render_text_with_outline(prompt_font, part4, PROMPT_COLOR, (255, 255, 255), 2)
        #surf3 = render_text_with_outline(prompt_font, part3, PROMPT_COLOR, (255, 255, 255), 2)
        total_width = surf1.get_width() + surf2.get_width() + surf3.get_width()
        max_height = max(surf1.get_height(), surf2.get_height(), surf3.get_height())
        prompt_combined = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        prompt_combined.blit(surf1, (0, 0))
        prompt_combined.blit(surf2, (surf1.get_width(), 0))
        prompt_combined.blit(surf3, (surf1.get_width() + surf2.get_width(), 0))
        # Position the prompt near the top of the screen (e.g., midtop at y=40)
        prompt_rect = prompt_combined.get_rect(midtop=(SCREEN_WIDTH // 2, 50))
        screen.blit(prompt_combined, prompt_rect)

        # Timer: same dynamic logic as before, but now centered above the prompt.
        if time_left > (2/3 * SIMULATION_DURATION_SECONDS):
            timer_color = (0, 255, 0)
        elif time_left > 10:
            timer_color = (255, 215, 0)
        else:
            timer_color = (255, 0, 0)
        timer_text = f"{time_left:05.2f}"
        progress = 1 - (time_left / SIMULATION_DURATION_SECONDS)
        current_timer_font_size = int(TIMER_FONT_SIZE_START + (TIMER_FONT_SIZE_END - TIMER_FONT_SIZE_START) * progress)
        timer_font = pygame.font.SysFont(None, current_timer_font_size)
        timer_surf = render_text_with_outline(timer_font, timer_text, timer_color, (255, 255, 255), 2)
        timer_margin = 8
        timer_rect = timer_surf.get_rect(midbottom=(SCREEN_WIDTH // 2, 113))
        screen.blit(timer_surf, timer_rect)

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

