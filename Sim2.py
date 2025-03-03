import os
import numpy as np
import wave
import pygame
import random

# -------------------------------------------------------
# Simulation Configuration
# -------------------------------------------------------
SCREEN_WIDTH = 432    # Window display width
SCREEN_HEIGHT = 768   # Window display height
RENDER_WIDTH = 1080   # Render resolution width
RENDER_HEIGHT = 1920  # Window rendering height
FPS = 60

PARTICLE_RADIUS = 15
PARTICLE_SPEED = 0.71
COLOR1_COUNT = 700    # Number of particles of COLOR1
COLOR2_COUNT = 700    # Number of particles of COLOR2
LAST_NUM_PARTICLES = 200  # Threshold for a forced color dominance swap

MIDDLE_LAST_NUM_PARTICLES = 255
MIDDLE_GROUP = 10

SECOND_LAST_NUM_PARTICLES = 65
SECOND_LAST_GROUP = 18

FINAL_LAST_NUM_PARTICLES = 0
FINAL_LAST_GROUP = 26

COLOR2 = (255,171,7)   # First color (Orange)
COLOR1 = (14,141,222)    # Second color (Blue?)
COLOR2_NAME = "Orange"
COLOR1_NAME = "Blue"

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

SHOW_SCOREBOARD = True
SHOW_WINNER_OVERLAY = True
SCOREBOARD_FONT_SIZE = 24

SOUND_COOLDOWN_MS = 100
SWAP_SOUND_COOLDOWN_MS = 500

last_collision_sound_tick = 0
last_swap_sound_tick = 0

AMBIENT_CHORDS = [
    [220, 261.63, 329.63],    
    [174.61, 220, 261.63],    
    [261.63, 329.63, 392.00], 
    [196.00, 246.94, 293.66]  
]
AMBIENT_DURATION = 32

# -------------------------------------------------------
# Helper: Save data to a WAV file
# -------------------------------------------------------
def save_wave(filename, data, sample_rate=44100):
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)  # Save as mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())

# -------------------------------------------------------
# Ambient Progression Generation
# -------------------------------------------------------
def generate_ambient_progression(filename, duration=AMBIENT_DURATION, volume=0.4, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Base Drone
    freqs = [60, 80, 100]
    tones = []
    for i, base_freq in enumerate(freqs):
        phase = 2 * np.pi * base_freq * t + 0.5 * np.sin(2 * np.pi * 0.4 * t + i * 0.3)
        tone = np.sin(phase)
        tones.append(tone)
    drone = np.mean(tones, axis=0)
    
    attack_time = 3.0
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    attack_env = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, attack_samples))
    envelope[:attack_samples] = attack_env
    release_env = 0.5 - 0.5 * np.cos(np.pi * np.linspace(1, 0, attack_samples))
    envelope[-attack_samples:] = release_env
    drone *= envelope

    # Chord Progression
    chords_count = len(AMBIENT_CHORDS)
    chord_duration = duration / chords_count
    chord_track = np.zeros_like(t)

    for i, chord in enumerate(AMBIENT_CHORDS):
        seg_start = int(i * chord_duration * sample_rate)
        seg_end = int((i + 1) * chord_duration * sample_rate)
        t_seg = np.linspace(0, chord_duration, seg_end - seg_start, endpoint=False)
        chord_signal = np.zeros_like(t_seg)
        for freq in chord:
            base = np.sin(2 * np.pi * (freq + 0.5*np.sin(2*np.pi*0.2*t_seg)) * t_seg)
            detuned = np.sin(2 * np.pi * (freq*1.005 + 0.5*np.sin(2*np.pi*0.2*t_seg)) * t_seg)
            note = (base + detuned) / 2.0
            chord_signal += note
        chord_signal /= len(chord)
        # Fade in/out in each chord segment
        fade_time = 0.5
        fade_samples = int(sample_rate * fade_time)
        env_seg = np.ones_like(t_seg)
        if fade_samples > 0 and fade_samples < len(t_seg) // 2:
            env_seg[:fade_samples] = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, fade_samples))
            env_seg[-fade_samples:] = 0.5 - 0.5 * np.cos(np.pi * np.linspace(1, 0, fade_samples))
        chord_signal *= env_seg
        chord_track[seg_start:seg_end] = chord_signal

    ambient = 0.6 * drone + 0.4 * chord_track
    ambient *= volume

    data = (ambient * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

# -------------------------------------------------------
# Collision Chime
# -------------------------------------------------------
def generate_chime(filename, frequency=400, duration=0.35, volume=0.07, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone_fundamental = np.sin(2 * np.pi * frequency * t)
    tone_overtone = 0.6 * np.sin(2 * np.pi * (frequency * 2) * t)
    tone = (0.7*tone_fundamental + tone_overtone) / 1.3
    
    attack_time = 0.03
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    envelope[:attack_samples] = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0,1,attack_samples))
    envelope[attack_samples:] = np.exp(-3 * (t[attack_samples:] - t[attack_samples]))
    tone *= envelope * volume
    data = (tone * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

# -------------------------------------------------------
# Victory Sound
# -------------------------------------------------------
def generate_victory(filename, duration=1.8, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    f1 = 440.0
    f2 = 523.25
    f3 = 659.26

    vibrato = 0.005 * np.sin(2 * np.pi * 1.0 * t)
    
    tone1 = np.sin(2 * np.pi * (f1 + vibrato) * t)
    tone1_detuned = np.sin(2 * np.pi * (f1*1.002 + vibrato) * t)
    tone1 = (tone1 + tone1_detuned) / 2
    
    tone2 = 0.8 * np.sin(2 * np.pi * (f2 + vibrato) * t)
    tone2_detuned = 0.8 * np.sin(2 * np.pi * (f2*1.002 + vibrato) * t)
    tone2 = (tone2 + tone2_detuned) / 2
    
    tone3 = 0.6 * np.sin(2 * np.pi * (f3 + vibrato) * t)
    tone3_detuned = np.sin(2 * np.pi * (f3*1.002 + vibrato) * t)
    tone3 = (tone3 + tone3_detuned) / 2

    chord = (tone1 + tone2 + tone3) / (1 + 0.8 + 0.6)
    
    attack_time = 0.1
    attack_samples = int(sample_rate * attack_time)
    release_samples = t.size - attack_samples
    env = np.ones_like(t)
    env[:attack_samples] = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, attack_samples))
    env[attack_samples:] = np.cos(np.linspace(0, np.pi/2, release_samples))
    chord *= env * volume
    data = (chord * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

# -------------------------------------------------------
# (New) Start Sound
# -------------------------------------------------------
def generate_start_sound(filename, frequency=600, duration=0.5, volume=0.15, sample_rate=44100):
    """
    A short, punchy start sound after the countdown finishes.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone_fundamental = np.sin(2 * np.pi * frequency * t)
    tone_overtone = 0.6 * np.sin(2 * np.pi * (frequency * 1.5) * t)
    tone = (tone_fundamental + tone_overtone) / 2.0
    
    # Simple envelope
    attack_time = 0.05
    attack_samples = int(sample_rate * attack_time)
    envelope = np.ones_like(t)
    envelope[:attack_samples] = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, attack_samples))
    envelope[attack_samples:] = np.exp(-5 * (t[attack_samples:] - t[attack_samples]))
    tone *= envelope * volume
    
    data = (tone * 32767).astype(np.int16)
    save_wave(filename, data, sample_rate)

# -------------------------------------------------------
# Generate or replace sound files
# -------------------------------------------------------
if os.path.exists("ambient.wav"):
    os.remove("ambient.wav")
generate_ambient_progression("ambient.wav", AMBIENT_DURATION, 0.55, 44100)

if os.path.exists("collision.wav"):
    os.remove("collision.wav")
generate_chime("collision.wav", 400, 0.35, 0.07, 44100)

if os.path.exists("victory.wav"):
    os.remove("victory.wav")
generate_victory("victory.wav", 1.8, 0.5, 44100)

# (New) Generate start sound
if os.path.exists("start.wav"):
    os.remove("start.wav")
generate_start_sound("start.wav", 600, 0.5, 0.15, 44100)

# -------------------------------------------------------
# Pygame and Mixer Initialization
# -------------------------------------------------------
pygame.init()

# If you want to force stereo, uncomment below:
# pygame.mixer.quit()
# pygame.mixer.init(frequency=44100, size=-16, channels=2)

pygame.mixer.init()

try:
    ambient_sound = pygame.mixer.Sound("ambient.wav")
    collision_sound = pygame.mixer.Sound("collision7.mp3")  # Provided file name in your code
    victory_sound = pygame.mixer.Sound("victory.wav")
    start_sound = pygame.mixer.Sound("start.wav")
except Exception as e:
    print("Error loading sound files:", e)
    ambient_sound = collision_sound = victory_sound = start_sound = None

if ambient_sound:
    ambient_sound.set_volume(0.67)
if collision_sound:
    collision_sound.set_volume(0.09)
if victory_sound:
    victory_sound.set_volume(0.4)
if start_sound:
    start_sound.set_volume(0.4)  # Adjust if desired

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Battle of Colors Simulation")

render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT)).convert()

dominant_color = None
submissive_color = None

# Helper function: Draw text with outline
def draw_text_with_border(surface, text, font, text_color, border_color, pos, border_width=2):
    for dx in [-border_width, 0, border_width]:
        for dy in [-border_width, 0, border_width]:
            if dx != 0 or dy != 0:
                border_surface = font.render(text, True, border_color)
                surface.blit(border_surface, (pos[0] + dx, pos[1] + dy))
    text_surface = font.render(text, True, text_color)
    surface.blit(text_surface, pos)

# Pre-render circles for performance
particle_surf_color1 = pygame.Surface((PARTICLE_RADIUS*2, PARTICLE_RADIUS*2), pygame.SRCALPHA)
pygame.draw.circle(particle_surf_color1, COLOR1, (PARTICLE_RADIUS, PARTICLE_RADIUS), PARTICLE_RADIUS)

particle_surf_color2 = pygame.Surface((PARTICLE_RADIUS*2, PARTICLE_RADIUS*2), pygame.SRCALPHA)
pygame.draw.circle(particle_surf_color2, COLOR2, (PARTICLE_RADIUS, PARTICLE_RADIUS), PARTICLE_RADIUS)

PARTICLE_SURF_MAP = {
    COLOR1: particle_surf_color1,
    COLOR2: particle_surf_color2
}

# -------------------------------------------------------
# Generate the SWAP SOUND with correct array depth
# -------------------------------------------------------
def generate_ambient_chord_swap_sound(chord, duration=0.8, volume=0.3, sample_rate=44100):
    """
    Creates a short chord-based sound to signal a swap.
    Adapts shape (mono/stereo) to match the mixer channels.
    """
    t = np.linspace(0, duration, int(sample_rate*duration), endpoint=False)
    chord_signal = np.zeros_like(t)

    for freq in chord:
        base = np.sin(2*np.pi*(freq + 0.5*np.sin(2*np.pi*0.2*t))*t)
        detuned = np.sin(2*np.pi*(freq*1.005 + 0.5*np.sin(2*np.pi*0.2*t))*t)
        chord_signal += (base + detuned)/2
    chord_signal /= len(chord)

    fade_time = 0.15
    fade_samples = int(sample_rate*fade_time)
    envelope = np.ones_like(t)
    if fade_samples > 0 and fade_samples < len(t)//2:
        envelope[:fade_samples] = 0.5 - 0.5*np.cos(np.pi*np.linspace(0,1,fade_samples))
        envelope[-fade_samples:] = 0.5 - 0.5*np.cos(np.pi*np.linspace(1,0,fade_samples))
    chord_signal *= envelope * volume

    data_mono = (chord_signal * 32767).astype(np.int16)

    mixer_init = pygame.mixer.get_init()  # returns (frequency, format, channels)
    if mixer_init is None:
        channels = 2
    else:
        _, _, channels = mixer_init

    if channels == 1:
        data = data_mono
    else:
        data = np.repeat(data_mono[:, np.newaxis], channels, axis=1)

    return pygame.sndarray.make_sound(data)

# -------------------------------------------------------
# Particle Class
# -------------------------------------------------------
class Particle:
    __slots__ = ('x','y','radius','color','vx','vy','last_conversion_time',
                 'final_x','final_y','start_y')  # Added final_x, final_y, start_y
    def __init__(self, x, y, radius, color, vx, vy, final_x, final_y, start_y):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.vx = vx
        self.vy = vy
        self.last_conversion_time = float('-inf')
        # For the falling animation
        self.final_x = final_x
        self.final_y = final_y
        self.start_y = start_y

    def move(self):
        """
        Normal movement inside the main simulation.
        Bounces off the edges, etc.
        """
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

    def resolve_collision(self, other, current_time, current_tick):
        global dominant_color, submissive_color, last_collision_sound_tick

        if self.color == dominant_color and other.color == submissive_color:
            if (current_time - self.last_conversion_time) >= CONVERSION_COOLDOWN:
                other.color = dominant_color
                other.last_conversion_time = current_time
                self.last_conversion_time = current_time
                if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    collision_sound.play()
                    last_collision_sound_tick = current_tick
        elif other.color == dominant_color and self.color == submissive_color:
            if (current_time - other.last_conversion_time) >= CONVERSION_COOLDOWN:
                self.color = dominant_color
                self.last_conversion_time = current_time
                other.last_conversion_time = current_time
                if collision_sound and current_tick - last_collision_sound_tick > SOUND_COOLDOWN_MS:
                    collision_sound.play()
                    last_collision_sound_tick = current_tick

# -------------------------------------------------------
# Create Particles
# -------------------------------------------------------
def create_particles(color1_count, color2_count, speed, seed=None):
    """
    Particles are assigned a final position (final_x, final_y) as originally.
    But their actual starting position will be above the screen (start_y),
    so they can 'fall' during the countdown.
    """
    if seed is not None:
        random.seed(seed)
    particles = []
    r = PARTICLE_RADIUS
    max_x = RENDER_WIDTH - r
    max_y = RENDER_HEIGHT - r

    for _ in range(color1_count):
        final_x = random.randint(r, max_x)
        final_y = random.randint(r, max_y)
        # Start above the screen, anywhere from -1000 up to just above 0 for variety
        start_y = random.randint(-1000, -r)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        # Create the particle with actual x=final_x, y=start_y (so it falls down)
        particles.append(Particle(final_x, start_y, r, COLOR1, vx, vy, final_x, final_y, start_y))

    for _ in range(color2_count):
        final_x = random.randint(r, max_x)
        final_y = random.randint(r, max_y)
        start_y = random.randint(-1000, -r)
        vx = speed if random.random() < 0.5 else -speed
        vy = speed if random.random() < 0.5 else -speed
        particles.append(Particle(final_x, start_y, r, COLOR2, vx, vy, final_x, final_y, start_y))

    return particles

def spatial_partitioning(particles):
    grid = {}
    size = GRID_SIZE
    for p in particles:
        cell = (int(p.x // size), int(p.y // size))
        grid.setdefault(cell, []).append(p)
    return grid

def check_collisions(grid, current_time, current_tick):
    for (cx, cy), cell_particles in grid.items():
        cp_len = len(cell_particles)
        for i in range(cp_len):
            p_i = cell_particles[i]
            xi = p_i.x
            yi = p_i.y
            ri = p_i.radius
            for j in range(i+1, cp_len):
                p_j = cell_particles[j]
                dx = xi - p_j.x
                dy = yi - p_j.y
                combined_radius = ri + p_j.radius
                if dx*dx + dy*dy < combined_radius*combined_radius:
                    p_i.resolve_collision(p_j, current_time, current_tick)
        for ox, oy in NEIGHBOR_OFFSETS:
            neighbor_cell = (cx+ox, cy+oy)
            if neighbor_cell in grid:
                neighbor_particles = grid[neighbor_cell]
                for p_i in cell_particles:
                    xi = p_i.x
                    yi = p_i.y
                    ri = p_i.radius
                    for p_j in neighbor_particles:
                        dx = xi - p_j.x
                        dy = yi - p_j.y
                        combined_radius = ri + p_j.radius
                        if dx*dx + dy*dy < combined_radius*combined_radius:
                            p_i.resolve_collision(p_j, current_time, current_tick)

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
        if current_tick - last_swap_sound_tick > SWAP_SOUND_COOLDOWN_MS:
            chord_duration = AMBIENT_DURATION / len(AMBIENT_CHORDS)
            chord_index = int((elapsed_time % AMBIENT_DURATION) // chord_duration)
            current_chord = AMBIENT_CHORDS[chord_index]
            swap_sound = generate_ambient_chord_swap_sound(current_chord, 0.8, 0.3, 44100)
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

# -------------------------------------------------------
# Main Loop
# -------------------------------------------------------
def main():
    global dominant_color, submissive_color

    determine_initial_dominance()
    particles = create_particles(COLOR1_COUNT, COLOR2_COUNT, PARTICLE_SPEED, seed=SEED)
    clock = pygame.time.Clock()

    scoreboard_font = pygame.font.SysFont(None, SCOREBOARD_FONT_SIZE)
    winner_font = pygame.font.SysFont(None, 55)

    winner_declared = False
    winner_text = ""

    # 1) Initial pause
    start_time = pygame.time.get_ticks()
    pause_duration = INITIAL_PAUSE_SECONDS * 1000
    while pygame.time.get_ticks() - start_time < pause_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
        render_surface.fill(BACKGROUND_COLOR)
        # Draw particles where they currently are (they're all off-screen at first in 'y')
        for particle in particles:
            particle.draw(render_surface)

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0,0))
        pygame.display.flip()
        clock.tick(FPS)

    # 2) Three-second countdown + falling animation
    #    Each second we flash the countdown number, play collision sound once, and let them fall 1/3 of the way.
    #    We break it into 3 intervals of 1 second each.
    countdown_font = pygame.font.SysFont(None, 100)
    total_countdown_ms = 3000

    # We track how far each particle should be along (0 to 1) in falling each second chunk.
    # For second i in [0..2], fraction from i/3 to (i+1)/3.
    for second in [3, 2, 1]:
        # Play collision sound once at the start of each second
        if collision_sound:
            collision_sound.play()

        segment_start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - segment_start_time < 1000:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    return

            # Elapsed in this 1-second chunk
            segment_elapsed = pygame.time.get_ticks() - segment_start_time
            fraction = segment_elapsed / 1000.0  # goes from 0 to 1 during this second

            # figure out how far along overall
            # If second=3 => this chunk is fraction of 0->1/3,
            # second=2 => fraction of 1/3->2/3, second=1 => fraction of 2/3->3/3
            # We'll invert it a bit: second=3 means chunk index=0, second=2 =>1, second=1 =>2
            chunk_index = 3 - second  # chunk_index in [0,1,2]
            start_frac = chunk_index / 3.0
            end_frac = (chunk_index + 1) / 3.0
            overall_progress = start_frac + (end_frac - start_frac)*fraction

            # Update the falling positions for all particles
            for p in particles:
                p.y = p.start_y + (p.final_y - p.start_y) * overall_progress

            # Draw
            render_surface.fill(BACKGROUND_COLOR)
            for p in particles:
                p.draw(render_surface)

            # Show the countdown number
            scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
            screen.blit(scaled_surface, (0,0))

            text_surf = countdown_font.render(str(second), True, (255,255,255))
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            screen.blit(text_surf, text_rect)

            pygame.display.flip()
            clock.tick(FPS)

    # 3) After countdown is done, play a starting sound
    if start_sound:
        start_sound.play()

    # 4) Now start the ambient loop & normal simulation
    if ambient_sound:
        ambient_sound.play(loops=-1)

    sim_start_time = pygame.time.get_ticks()
    running = True
    while running:
        current_tick = pygame.time.get_ticks()
        elapsed_time = (current_tick - sim_start_time)/1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # Normal checks
        check_last_particles(particles, elapsed_time)
        grid = spatial_partitioning(particles)
        check_collisions(grid, elapsed_time, current_tick)

        render_surface.fill(BACKGROUND_COLOR)
        color1_count = 0
        color2_count = 0

        # Normal movement now
        for particle in particles:
            particle.move()
            particle.draw(render_surface)
            if particle.color == COLOR1:
                color1_count += 1
            else:
                color2_count += 1

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0,0))

        if SHOW_SCOREBOARD:
            left_text = f"{COLOR1_NAME}: {color1_count}"
            right_text = f"{COLOR2_NAME}: {color2_count}"
            left_pos = (23, 23)
            draw_text_with_border(screen, left_text, scoreboard_font, COLOR1, (255,255,255), left_pos)
            right_text_w, _ = scoreboard_font.size(right_text)
            right_pos = (SCREEN_WIDTH - right_text_w - 23, 23)
            draw_text_with_border(screen, right_text, scoreboard_font, COLOR2, (255,255,255), right_pos)

        # Check if winner
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

        # Show winner overlay
        if SHOW_WINNER_OVERLAY and winner_declared and winner_text:
            text_surf = winner_font.render(winner_text, True, (255,255,255))
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            screen.blit(text_surf, text_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
