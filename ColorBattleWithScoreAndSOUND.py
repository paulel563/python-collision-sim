import os
import numpy as np
import wave
import pygame
import random

# -------------------------------------------------------
# Original Simulation Configuration
# -------------------------------------------------------
SCREEN_WIDTH = 432    # Window display width
SCREEN_HEIGHT = 768   # Window display height
RENDER_WIDTH = 1080   # Render resolution width
RENDER_HEIGHT = 1920  # Render resolution height
FPS = 60

PARTICLE_RADIUS = 16
PARTICLE_SPEED = 0.7
COLOR1_COUNT = 600    # Initial number of particles in COLOR1
COLOR2_COUNT = 600    # Initial number of particles in COLOR2
LAST_NUM_PARTICLES = 160  # Number of submissive particles left to trigger a reversal

MIDDLE_LAST_NUM_PARTICLES = 250  # Threshold for the middle phase
MIDDLE_GROUP = 8                 # Time in seconds to switch to the middle phase

SECOND_LAST_NUM_PARTICLES = 50   # Threshold for the second-to-last phase
SECOND_LAST_GROUP = 11           # Time in seconds to switch phases

FINAL_LAST_NUM_PARTICLES = 0     # Final threshold for the last phase
FINAL_LAST_GROUP = 31            # Time in seconds to switch phases

# Colors and Names
COLOR2 = (0, 255, 255)    # First color (Cyan)
COLOR1 = (255, 69, 0)     # Second color (Orange Red)
COLOR2_NAME = "Cyan"
COLOR1_NAME = "Orange Red"

BACKGROUND_COLOR = (0, 0, 0)  # Background color

SEED = 4  # Seed for random

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
# Toggles and Font Sizes
# -------------------------------------------------------
SHOW_SCOREBOARD = True       # Toggle scoreboard display on/off
SHOW_WINNER_OVERLAY = True   # Toggle winner overlay on/off

SCOREBOARD_FONT_SIZE = 24    # Scoreboard font size

# -------------------------------------------------------
# Sound Design Configuration (Cooldowns in milliseconds)
# -------------------------------------------------------
SOUND_COOLDOWN_MS = 100      # Minimum time between collision sounds
SWAP_SOUND_COOLDOWN_MS = 500 # Minimum time between swap sounds

# Global timing variables for sounds
last_collision_sound_tick = 0
last_swap_sound_tick = 0

# -------------------------------------------------------
# Helper Function to Save WAV Files
# -------------------------------------------------------
def save_wave(filename, data, sample_rate=44100):
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)        # mono
        wf.setsampwidth(2)        # 16-bit samples
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())

# -------------------------------------------------------
# NEW: Ambient Sound Generation with a Chord Progression
# -------------------------------------------------------
def generate_ambient_progression(filename, duration=32, volume=0.2, sample_rate=44100):
    """
    Generates an evolving ambient sound that blends a low–frequency drone with
    a slowly changing chord progression. This creates a relaxing, musical background.
    
    The drone is formed from three sine waves (80, 100, and 120 Hz) with gentle vibrato.
    The chord progression (Am – F – C – G) is split evenly over the duration.
    """
    # Create time vector for the full duration
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # --- Base Drone Layer ---
    freqs = [80, 100, 120]
    tones = []
    for i, base_freq in enumerate(freqs):
        # Apply gentle vibrato with a slight phase offset
        phase = 2 * np.pi * base_freq * t + 0.8 * np.sin(2 * np.pi * 0.4 * t + i * 0.3)
        tone = np.sin(phase)
        tones.append(tone)
    drone = np.mean(tones, axis=0)
    
    # Apply a slow fade in/out (3 seconds each)
    attack_time = 3.0
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[-attack_samples:] = np.linspace(1, 0, attack_samples)
    drone *= envelope

    # --- Chord Progression Layer ---
    # Define chord progression: Am, F, C, G
    progression = [
        [220, 261.63, 329.63],   # A minor: A3, C4, E4
        [174.61, 220, 261.63],    # F major: F3, A3, C4
        [261.63, 329.63, 392.00],  # C major: C4, E4, G4
        [196.00, 246.94, 293.66]   # G major: G3, B3, D4
    ]
    chords_count = len(progression)
    chord_duration = duration / chords_count

    chord_track = np.zeros_like(t)
    for i, chord in enumerate(progression):
        seg_start = int(i * chord_duration * sample_rate)
        seg_end = int((i + 1) * chord_duration * sample_rate)
        t_seg = np.linspace(0, chord_duration, seg_end - seg_start, endpoint=False)
        chord_signal = np.zeros_like(t_seg)
        for freq in chord:
            # Each note gets a gentle vibrato
            chord_signal += np.sin(2 * np.pi * (freq + 0.5 * np.sin(2 * np.pi * 0.2 * t_seg)) * t_seg)
        chord_signal /= len(chord)
        # Smooth fade in/out for the chord segment (0.5 seconds)
        fade_time = 0.5
        fade_samples = int(sample_rate * fade_time)
        env_seg = np.ones_like(t_seg)
        if fade_samples > 0 and fade_samples < len(t_seg) // 2:
            env_seg[:fade_samples] = np.linspace(0, 1, fade_samples)
            env_seg[-fade_samples:] = np.linspace(1, 0, fade_samples)
        chord_signal *= env_seg
        chord_track[seg_start:seg_end] = chord_signal

    # --- Mix the Two Layers ---
    # 60% drone and 40% chord progression
    ambient = 0.6 * drone + 0.4 * chord_track
    ambient *= volume

    data = (ambient * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

# -------------------------------------------------------
# UPDATED SOUND GENERATION FUNCTIONS (Collision, Sweep, Victory)
# -------------------------------------------------------

def generate_chime(filename, frequency=400, duration=0.25, volume=0.2, sample_rate=44100):
    """
    Generates a gentle collision "chime" with added harmonic overtones.
    The sound is designed to be like a soft bell tone with a smooth, slightly longer decay.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone_fundamental = np.sin(2 * np.pi * frequency * t)
    tone_overtone = 0.6 * np.sin(2 * np.pi * (frequency * 2) * t)
    tone = (0.7 * tone_fundamental + tone_overtone) / 1.3
    
    attack_time = 0.02
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[attack_samples:] = np.exp(-6 * (t[attack_samples:] - t[attack_samples]))
    tone *= envelope * volume
    data = (tone * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

def generate_sweep(filename, start_freq=300, end_freq=600, duration=0.4, volume=0.4, sample_rate=44100):
    """
    Generates a frequency sweep for dominance swaps. This version uses a linear sweep
    over a slightly extended duration, with added harmonic content for a more rounded tone.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    phase = 2 * np.pi * (start_freq * t + 0.5 * (end_freq - start_freq) * (t**2) / duration)
    tone_primary = np.sin(phase)
    tone_harmonic = 0.4 * np.sin(phase * 1.5)
    tone = (tone_primary + tone_harmonic) / 1.4

    attack_time = 0.05
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[attack_samples:] = np.exp(-4 * (t[attack_samples:] - t[attack_samples]))
    tone *= envelope * volume
    data = (tone * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

def generate_victory(filename, duration=1.2, volume=0.5, sample_rate=44100):
    """
    Generates a smooth victory tone in the form of a soft chord.
    Three harmonically related sine waves (forming a gentle chord) play together,
    with a slow fade-out and a touch of vibrato to enhance the soothing quality.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    f1 = 660       # Fundamental
    f2 = 880       # A perfect fifth above (approximately)
    f3 = 990       # A gentle third/higher overtone

    vibrato = 0.005 * np.sin(2 * np.pi * 1.0 * t)  # very gentle vibrato
    
    tone1 = np.sin(2 * np.pi * (f1 + vibrato) * t)
    tone2 = 0.8 * np.sin(2 * np.pi * (f2 + vibrato) * t)
    tone3 = 0.6 * np.sin(2 * np.pi * (f3 + vibrato) * t)
    chord = (tone1 + tone2 + tone3) / (1 + 0.8 + 0.6)
    
    attack_time = 0.05
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[attack_samples:] = np.linspace(1, 0, t.size - attack_samples)
    chord *= envelope * volume
    data = (chord * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

# -------------------------------------------------------
# Generate or Replace Sound Files (Remove old files if they exist)
# -------------------------------------------------------
if os.path.exists("ambient.wav"):
    os.remove("ambient.wav")
# Use the new ambient progression for a relaxing background
generate_ambient_progression("ambient.wav", duration=32, volume=0.2, sample_rate=44100)

if os.path.exists("collision.wav"):
    os.remove("collision.wav")
generate_chime("collision.wav", frequency=400, duration=0.25, volume=0.2)

if os.path.exists("swap.wav"):
    os.remove("swap.wav")
generate_sweep("swap.wav", start_freq=300, end_freq=600, duration=0.4, volume=0.4)

if os.path.exists("victory.wav"):
    os.remove("victory.wav")
generate_victory("victory.wav", duration=1.2, volume=0.5)

# -------------------------------------------------------
# Pygame and Mixer Initialization
# -------------------------------------------------------
pygame.init()
pygame.mixer.init()

# Load sound assets (the files were generated above)
try:
    ambient_sound = pygame.mixer.Sound("ambient.wav")
    collision_sound = pygame.mixer.Sound("collision.wav")
    swap_sound = pygame.mixer.Sound("swap.wav")
    victory_sound = pygame.mixer.Sound("victory.wav")
except Exception as e:
    print("Error loading sound files:", e)
    ambient_sound = collision_sound = swap_sound = victory_sound = None

# Set volumes (adjust as needed)
if ambient_sound:
    ambient_sound.set_volume(0.2)
if collision_sound:
    collision_sound.set_volume(0.3)
if swap_sound:
    swap_sound.set_volume(0.4)
if victory_sound:
    victory_sound.set_volume(0.5)

# Start ambient sound looping
if ambient_sound:
    ambient_sound.play(loops=-1)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Battle of Colors Simulation")

# Create a high-resolution rendering surface
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

dominant_color = None
submissive_color = None

# -------------------------------------------------------
# Helper Function: Draw Text with a White Border
# -------------------------------------------------------
def draw_text_with_border(surface, text, font, text_color, border_color, pos, border_width=2):
    for dx in [-border_width, 0, border_width]:
        for dy in [-border_width, 0, border_width]:
            if dx != 0 or dy != 0:
                border_surface = font.render(text, True, border_color)
                surface.blit(border_surface, (pos[0] + dx, pos[1] + dy))
    text_surface = font.render(text, True, text_color)
    surface.blit(text_surface, pos)

# -------------------------------------------------------
# Pre-render Particle Surfaces
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
# Particle Class and Simulation Functions
# -------------------------------------------------------
class Particle:
    __slots__ = ('x', 'y', 'radius', 'color', 'vx', 'vy', 'last_conversion_time')

    def __init__(self, x, y, radius, color, vx, vy):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.vx = vx
        self.vy = vy        
        self.last_conversion_time = float('-inf')

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
        surf = PARTICLE_SURF_MAP[self.color]
        surface.blit(surf, (int(self.x - self.radius), int(self.y - self.radius)))

    def check_collision(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        distance_squared = dx * dx + dy * dy
        combined_radius = self.radius + other.radius
        return distance_squared < (combined_radius * combined_radius)

    def resolve_collision(self, other, current_time):
        global dominant_color, submissive_color, last_collision_sound_tick

        if self.color == dominant_color and other.color == submissive_color:
            if (current_time - self.last_conversion_time) >= CONVERSION_COOLDOWN:
                other.color = dominant_color
                other.last_conversion_time = current_time
                self.last_conversion_time = current_time

                current_tick = pygame.time.get_ticks()
                if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    collision_sound.play()
                    last_collision_sound_tick = current_tick

        elif other.color == dominant_color and self.color == submissive_color:
            if (current_time - other.last_conversion_time) >= CONVERSION_COOLDOWN:
                self.color = dominant_color
                self.last_conversion_time = current_time
                other.last_conversion_time = current_time

                current_tick = pygame.time.get_ticks()
                if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    collision_sound.play()
                    last_collision_sound_tick = current_tick

def create_particles(color1_count, color2_count, speed, seed=None):
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
    for (cx, cy), cell_particles in grid.items():
        cp_len = len(cell_particles)
        for i in range(cp_len):
            p_i = cell_particles[i]
            for j in range(i + 1, cp_len):
                p_j = cell_particles[j]
                if p_i.check_collision(p_j):
                    p_i.resolve_collision(p_j, current_time)
        for ox, oy in NEIGHBOR_OFFSETS:
            neighbor = (cx + ox, cy + oy)
            if neighbor in grid:
                neighbor_particles = grid[neighbor]
                for p_i in cell_particles:
                    for p_j in neighbor_particles:
                        if p_i.check_collision(p_j):
                            p_i.resolve_collision(p_j, current_time)

last_dominant = None

def check_last_particles(particles, elapsed_time):
    global dominant_color, submissive_color, last_swap_sound_tick, last_dominant

    if elapsed_time > FINAL_LAST_GROUP:
        threshold = FINAL_LAST_NUM_PARTICLES
    elif elapsed_time > SECOND_LAST_GROUP:
        threshold = SECOND_LAST_NUM_PARTICLES
    elif elapsed_time > MIDDLE_GROUP:
        threshold = MIDDLE_LAST_NUM_PARTICLES
    else:
        threshold = LAST_NUM_PARTICLES

    sc = submissive_color
    submissive_count = sum(1 for p in particles if p.color == sc)

    previous_dominant = dominant_color
    if submissive_count <= threshold:
        dominant_color, submissive_color = submissive_color, dominant_color

    if previous_dominant != dominant_color:
        current_tick = pygame.time.get_ticks()
        if swap_sound and current_tick - last_swap_sound_tick > SWAP_SOUND_COOLDOWN_MS:
            swap_sound.play()
            last_swap_sound_tick = current_tick
        last_dominant = dominant_color

def determine_initial_dominance():
    global dominant_color, submissive_color, last_dominant
    if COLOR1_COUNT < COLOR2_COUNT:
        dominant_color, submissive_color = COLOR1, COLOR2
    elif COLOR2_COUNT < COLOR1_COUNT:
        dominant_color, submissive_color = COLOR2, COLOR1
    else:
        dominant_color, submissive_color = COLOR1, COLOR2
    last_dominant = dominant_color

def main():
    global dominant_color, submissive_color

    determine_initial_dominance()
    particles = create_particles(COLOR1_COUNT, COLOR2_COUNT, PARTICLE_SPEED, seed=SEED)
    clock = pygame.time.Clock()

    scoreboard_font = pygame.font.SysFont(None, SCOREBOARD_FONT_SIZE)
    winner_font = pygame.font.SysFont(None, 72)

    winner_declared = False
    winner_text = ""

    start_time = pygame.time.get_ticks()
    pause_duration = INITIAL_PAUSE_SECONDS * 1000
    while pygame.time.get_ticks() - start_time < pause_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
        render_surface.fill(BACKGROUND_COLOR)
        for particle in particles:
            particle.draw(render_surface)
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

    start_time = pygame.time.get_ticks()
    running = True
    while running:
        current_ticks = pygame.time.get_ticks()
        elapsed_time = (current_ticks - start_time) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        check_last_particles(particles, elapsed_time)
        grid = spatial_partitioning(particles)
        check_collisions(grid, elapsed_time)

        render_surface.fill(BACKGROUND_COLOR)
        color1_count = 0
        color2_count = 0

        for particle in particles:
            particle.move()
            particle.draw(render_surface)
            if particle.color == COLOR1:
                color1_count += 1
            else:
                color2_count += 1

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        if SHOW_SCOREBOARD:
            left_text = f"{COLOR1_NAME}: {color1_count}"
            right_text = f"{COLOR2_NAME}: {color2_count}"
            left_pos = (15, 15)
            draw_text_with_border(screen, left_text, scoreboard_font, COLOR1, (255, 255, 255), left_pos)
            right_text_width, _ = scoreboard_font.size(right_text)
            right_pos = (SCREEN_WIDTH - right_text_width - 15, 15)
            draw_text_with_border(screen, right_text, scoreboard_font, COLOR2, (255, 255, 255), right_pos)

        if not winner_declared:
            if color1_count == 0:
                winner_declared = True
                winner_text = f"{COLOR2_NAME} WINS!"
                if victory_sound:
                    victory_sound.play()
            elif color2_count == 0:
                winner_declared = True
                winner_text = f"{COLOR1_NAME} WINS!"
                if victory_sound:
                    victory_sound.play()

        if SHOW_WINNER_OVERLAY and winner_declared and winner_text:
            text_surface = winner_font.render(winner_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text_surface, text_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
