import math
import random
import colorsys
import pygame
from pygame import Vector2, DOUBLEBUF, mixer
from Box2D import b2World, b2ContactListener, b2EdgeShape

###############################################################################
# CONFIGURABLE VARIABLES
###############################################################################
# Random seed
SEED = 2

# Screen settings
SCREEN_WIDTH = 432       # Display window width
SCREEN_HEIGHT = 768      # Display window height
SCREEN_BACKGROUND_COLOR = (0, 0, 29)

# Physics and Pygame updates
FRAMERATE = 60
PPM = 10.0  # Pixels per meter

# Gravity rotates around to "bounce"
GRAVITY_MAG = 95        # Gravity magnitude
GRAVITY_ROT_SPEED = 0.0005  # How fast gravity rotates

# Ball settings
BALL_RADIUS = 1
BALL_COLOR = (255, 255, 255)

# Rings settings
NUM_RINGS = 40
INITIAL_RING_RADIUS = 8
RING_DISTANCE = 1.5       # You can change this to increase/decrease ring spacing
INITIAL_ROTATION_SPEED = 1.90
ROTATION_SPEED_MULTIPLIER = 1.005
INITIAL_HUE = 0
RING_LINE_THICKNESS = 8

# For the ring shape logic in the code:
RING_SEGMENT_COUNT = 50
TRIANGLE_SIZE = 3
SQUARE_SIZE = 4

# NEW VARIABLE: the max angle (0..360) where edges are drawn. The rest is the gap.
CIRCLE_GAP_END_ANGLE = 299.0

# Explosion / Particle settings
PARTICLE_COUNT = 9
PARTICLE_SIZE_MIN = 0.5
PARTICLE_SIZE_MAX = 2
PARTICLE_ANGLE_MIN = 0
PARTICLE_ANGLE_MAX = 360
PARTICLE_SPEED_MIN = 0.6
PARTICLE_SPEED_MAX = 1
PARTICLE_LIFE_MIN = 100
PARTICLE_LIFE_MAX = 1000

# Initial pause at the start of the game (in seconds)
INITIAL_PAUSE_TIME = 3.0

# SOUND AND VOLUME SETTINGS
COLLISION_VOLUME = 0.69
DESTROY_VOLUME = 0.5
DESTROY_SOUND_FILE = "levelup.wav"
#DESTROY_SOUND_FILE = "discord.mp3"
#DESTROY_SOUND_FILE = "assets/Mustard.mp3"
"""
COLLISION_SOUND_FILES = [
    "assets/(1).wav",
    "assets/(2).wav",
    "assets/(3).wav"
]
"""
"""
COLLISION_SOUND_FILES = [
    "assets/Untitled.wav",
    "assets/Untitled (1).wav",
    "assets/Untitled (2).wav",
    "assets/Untitled (3).wav",
    "assets/Untitled (4).wav",
    "assets/Untitled (5).wav",
    "assets/Untitled (6).wav",
    "assets/Untitled (7).wav",
    "assets/Untitled (8).wav",
    "assets/Untitled (9).wav",
    "assets/Untitled (10).wav",
    "assets/Untitled (11).wav"
]
"""
COLLISION_SOUND_FILES = [
    "wav/a1s.wav",
    "wav/b1.wav",
    "wav/c2.wav",
    "wav/d1s.wav",
    "wav/e1.wav",
    "wav/f1s.wav",
    "wav/g1s.wav"
]

# IMPORTANT: For SOUND_OPTION 2, the collision snippet file must support playback offset.
# WAV files typically do not support the "start" parameter correctly.
# Convert your snippet file to OGG or MP3.
#COLLISION_SOUND2 = "ed.ogg"  # converted to OGG
COLLISION_SOUND2 = "calmloop.mp3"  # converted to OGG

# NEW SOUND OPTION SETTINGS
SOUND_OPTION = 1  # 1: current behavior, 2: new snippet-based behavior
#SNIPPET_DURATION = 0.45  # snippet duration in seconds (adjust as needed)
SNIPPET_DURATION = 0.22  # snippet duration in seconds (adjust as needed)
COLLISION_OVERLAP_BUFFER = 0.01  # collision overlap buffer in seconds (10 ms)

# TEXT RENDER SETTINGS
TEXT_COLOR = (255, 255, 255)
TEXT_POSITION = (SCREEN_WIDTH // 2, 70)  # Centered horizontally, 80px from top

# TIMER SETTINGS
TIMER_DURATION = 35.0  # Default timer length in seconds (can be changed)
TIMER_POSITION = (SCREEN_WIDTH // 2, 37)  # Timer displayed above bounce count

# New Color Setting: 1 for current rainbow behavior, 2 for custom gradient.
COLOR_SETTING = 2  # Change this to 2 for gradient

# NEW SHRINKING VARIABLES
SHRINK_SPEED1 = 5.00   # Fast shrink speed (from current radius down to INITIAL_RING_RADIUS)
SHRINK_SPEED2 = 1.75   # Slow shrink speed (from INITIAL_RING_RADIUS to 0)
SHRINK_DELAY  = 0.20   # Delay (in seconds) after an inner ring is popped before shrinking starts

# Define the gradient function for COLOR_SETTING 2.
# This example creates a gradient from green to blue.
def gradient_color(t, color_start=(0, 255, 0), color_end=(0, 0, 255)):
    # t should be between 0 and 1
    r = int(color_start[0] * (1 - t) + color_end[0] * t)
    g = int(color_start[1] * (1 - t) + color_end[1] * t)
    b = int(color_start[2] * (1 - t) + color_end[2] * t)
    return (r, g, b)

# Initialize the random seed
random.seed(SEED)

###############################################################################
# MyContactListener
###############################################################################
class MyContactListener(b2ContactListener):
    def __init__(self):
        super(MyContactListener, self).__init__()
        self.collisions = []

    def BeginContact(self, contact):
        fixtureA = contact.fixtureA
        fixtureB = contact.fixtureB
        bodyA = fixtureA.body
        bodyB = fixtureB.body

        # Check if one of the fixtures is the ring and the other is the ball
        if (isinstance(bodyA.userData, Ring) and isinstance(bodyB.userData, Ball)) \
           or (isinstance(bodyA.userData, Ball) and isinstance(bodyB.userData, Ring)):
            self.collisions.append((bodyA, bodyB))

    def EndContact(self, contact):
        pass

###############################################################################
# Utils
###############################################################################
class Utils:
    def __init__(self):
        pygame.init()
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT

        self.screen = pygame.display.set_mode((self.width, self.height), DOUBLEBUF, 16)

        self.dt = 0
        self.clock = pygame.time.Clock()

        self.PPM = PPM  # Pixels per meter
        self.world = b2World(gravity=(0, -GRAVITY_MAG), doSleep=True)

        self.contactListener = MyContactListener()
        self.world.contactListener = self.contactListener

        self.gravityAngle = -math.pi / 2  # start direction (straight down)

    def to_Pos(self, pos):
        return (pos[0] * self.PPM, self.height - (pos[1] * self.PPM))

    def from_Pos(self, pos):
        return (pos[0] / self.PPM, (self.height - pos[1]) / self.PPM)

    def calDeltaTime(self):
        t = self.clock.tick(FRAMERATE)
        self.dt = t / 1000
        self.gravityAngle += GRAVITY_ROT_SPEED * self.dt
        gx = GRAVITY_MAG * math.cos(self.gravityAngle)
        gy = GRAVITY_MAG * math.sin(self.gravityAngle)
        self.world.gravity = (gx, gy)

    def deltaTime(self):
        return self.dt

    def hueToRGB(self, hue):
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        return (int(r * 255), int(g * 255), int(b * 255))

###############################################################################
# Ball
###############################################################################
class Ball:
    def __init__(self, pos, radius, color):
        global utils
        self.color = color
        self.radius = radius
        self.circle_body = utils.world.CreateDynamicBody(position=utils.from_Pos((pos.x, pos.y)))
        self.circle_shape = self.circle_body.CreateCircleFixture(
            radius=self.radius, density=1, friction=0.0, restitution=1.0
        )
        self.circle_body.userData = self
        self.destroyFlag = False

    def draw(self):
        global utils
        for fixture in self.circle_body.fixtures:
            self.draw_circle(fixture.shape, self.circle_body, fixture)

    def draw_circle(self, circle, body, fixture):
        global utils
        position = utils.to_Pos(body.transform * circle.pos)
        pygame.draw.circle(utils.screen, self.color, [int(x) for x in position],
                           int(circle.radius * utils.PPM))

    def getPos(self):
        global utils
        p = utils.to_Pos(self.circle_body.position)
        return Vector2(p[0], p[1])

###############################################################################
# Particle and Explosion
###############################################################################
class Particle:
    def __init__(self, x, y, color):
        self.radius = random.uniform(PARTICLE_SIZE_MIN, PARTICLE_SIZE_MAX)
        angle = random.uniform(PARTICLE_ANGLE_MIN, PARTICLE_ANGLE_MAX)
        speed = random.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
        self.x = x
        self.y = y
        self.color = color
        self.vel_x = math.cos(math.radians(angle)) * speed
        self.vel_y = math.sin(math.radians(angle)) * speed
        self.life = random.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX)

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.life -= 1

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.radius))

class Explosion:
    def __init__(self, x, y, color):
        self.particles = []
        COLORS = [color]
        for _ in range(PARTICLE_COUNT):
            chosen_color = random.choice(COLORS)
            particle = Particle(x, y, chosen_color)
            self.particles.append(particle)

    def update(self):
        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self):
        global utils
        for particle in self.particles:
            particle.draw(utils.screen)

###############################################################################
# Ring
###############################################################################
class Ring:
    def __init__(self, pos, radius, rotateDir, size, hue):
        global utils
        self.color = (255, 255, 255)
        self.radius = radius
        self.rotateDir = rotateDir
        self.size = size
        self.vertices = []
        for i in range(self.size):
            angle = i * (2 * math.pi / self.size)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            self.vertices.append((x, y))

        self.body = utils.world.CreateStaticBody(position=utils.from_Pos(pos))
        self.body.userData = self

        self.create_edge_shape()
        self.hue = hue
        self.destroyFlag = False

    def create_edge_shape(self):
        if self.size == RING_SEGMENT_COUNT:
            for i in range(self.size):
                angle = i * (360 / self.size)
                if 0 <= angle <= CIRCLE_GAP_END_ANGLE:
                    v1 = self.vertices[i]
                    v2 = self.vertices[(i + 1) % self.size]
                    edge = b2EdgeShape(vertices=[v1, v2])
                    self.body.CreateEdgeFixture(
                        shape=edge, density=1, friction=0.0, restitution=1.0
                    )
        if self.size == TRIANGLE_SIZE or self.size == SQUARE_SIZE:
            for i in range(self.size):
                if i == 0:
                    holeSize = 4
                    v1 = Vector2(self.vertices[i])
                    v2 = Vector2(self.vertices[(i + 1) % self.size])
                    length = (v2 - v1).length()
                    dir_vec = (v2 - v1).normalize()
                    mV1 = v1 + dir_vec * (length / 2 - holeSize)
                    mV2 = v1 + dir_vec * (length / 2 + holeSize)
                    edge = b2EdgeShape(vertices=[v1, mV1])
                    self.body.CreateEdgeFixture(
                        shape=edge, density=1, friction=0.0, restitution=1.0
                    )
                    edge = b2EdgeShape(vertices=[mV2, v2])
                    self.body.CreateEdgeFixture(
                        shape=edge, density=1, friction=0.0, restitution=1.0
                    )
                else:
                    v1 = self.vertices[i]
                    v2 = self.vertices[(i + 1) % self.size]
                    edge = b2EdgeShape(vertices=[v1, v2])
                    self.body.CreateEdgeFixture(
                        shape=edge, density=1, friction=0.0, restitution=1.0
                    )

    def update_collision_shape(self):
        # Remove all existing fixtures and re-create them based on the new radius
        for fixture in list(self.body.fixtures):
            self.body.DestroyFixture(fixture)
        self.vertices = []
        for i in range(self.size):
            angle = i * (2 * math.pi / self.size)
            x = self.radius * math.cos(angle)
            y = self.radius * math.sin(angle)
            self.vertices.append((x, y))
        self.create_edge_shape()

    def update_shrink(self, dt, min_allowed=0):
        old_radius = self.radius
        # Calculate the new radius using the two-phase shrink speeds.
        if self.radius > INITIAL_RING_RADIUS:
            new_radius = max(self.radius - SHRINK_SPEED1 * dt, INITIAL_RING_RADIUS)
        else:
            new_radius = max(self.radius - SHRINK_SPEED2 * dt, 0)
        # Ensure the new radius is not below the minimum allowed value.
        if new_radius < min_allowed:
            new_radius = min_allowed
        self.radius = new_radius
        if self.radius != old_radius:
            self.update_collision_shape()

    def draw(self, paused=False):
        global utils, COLOR_SETTING
        if not paused:
            self.hue = (self.hue + utils.deltaTime() / 5) % 1
            self.body.angle += self.rotateDir * utils.deltaTime()
        if COLOR_SETTING == 1:
            self.color = utils.hueToRGB(self.hue)
        elif COLOR_SETTING == 2:
            # Use the custom gradient; change the start/end colors as needed.
            self.color = gradient_color(self.hue, color_start=(0,255,0), color_end=(0,0,255))
        self.draw_edges()

    def draw_edges(self):
        global utils
        for fixture in self.body.fixtures:
            v1 = utils.to_Pos(self.body.transform * fixture.shape.vertices[0])
            v2 = utils.to_Pos(self.body.transform * fixture.shape.vertices[1])
            pygame.draw.line(utils.screen, self.color, v1, v2, RING_LINE_THICKNESS)

    def spawParticles(self):
        global utils
        particles = []
        center = Vector2(utils.width / 2, utils.height / 2)
        for i in range(0, 360, 5):
            x = math.cos(math.radians(i)) * self.radius * 10
            y = math.sin(math.radians(i)) * self.radius * 10
            pos = center + Vector2(x, y)
            exp = Explosion(pos.x, pos.y, self.color)
            particles.append(exp)
        return particles

###############################################################################
# Sounds
###############################################################################
class Sounds:
    def __init__(self):
        mixer.init()
        self.destroySound = pygame.mixer.Sound(DESTROY_SOUND_FILE)
        self.destroySound.set_volume(DESTROY_VOLUME)

        if SOUND_OPTION == 1:
            self.sounds = [pygame.mixer.Sound(f) for f in COLLISION_SOUND_FILES]
            for s in self.sounds:
                s.set_volume(COLLISION_VOLUME)
            self.i = 0
        elif SOUND_OPTION == 2:
            self.collision_file = COLLISION_SOUND2
            pygame.mixer.music.load(self.collision_file)
            self.collisionSoundLength = pygame.mixer.Sound(self.collision_file).get_length()
            pygame.mixer.music.set_volume(COLLISION_VOLUME)
            self.current_pos = 0.0
            self.last_collision_time = -10000
            self.snippet_end_time = 0

    def play(self):
        if SOUND_OPTION == 1:
            for sound in self.sounds:
                sound.stop()
            sound = self.sounds[self.i]
            sound.play()
            self.i = (self.i + 1) % len(self.sounds)
        elif SOUND_OPTION == 2:
            current_time = pygame.time.get_ticks()
            if pygame.mixer.music.get_busy():
                return
            if (current_time - self.last_collision_time) < (COLLISION_OVERLAP_BUFFER * 1000):
                return
            pygame.mixer.music.stop()
            self.last_collision_time = current_time
            remaining_time = self.collisionSoundLength - self.current_pos
            duration = min(SNIPPET_DURATION, remaining_time)
            pygame.mixer.music.play(start=self.current_pos)
            self.snippet_end_time = current_time + int(duration * 1000)

    def update(self):
        if SOUND_OPTION == 2:
            current_time = pygame.time.get_ticks()
            if self.snippet_end_time and current_time >= self.snippet_end_time:
                pygame.mixer.music.stop()
                self.snippet_end_time = 0
                self.current_pos += SNIPPET_DURATION
                if self.current_pos >= self.collisionSoundLength:
                    self.current_pos = 0.0

    def playDestroySound(self):
        self.destroySound.play()

###############################################################################
# Game
###############################################################################
class Game:
    def __init__(self):
        global utils
        global sounds

        self.center = Vector2(utils.width / 2, utils.height / 2)
        self.ball = Ball(Vector2(utils.width / 2, utils.height / 2),
                         BALL_RADIUS, BALL_COLOR)
        self.particles = []
        self.rings = []
        self.collision_count = 0
        self.collision_happened_last_frame = False
        self.font = pygame.font.Font(None, 36)
        self.elapsed_time = 0  # Accumulates dt for timing
        self.last_pop_time = None  # Time when the innermost ring was popped
        radius = INITIAL_RING_RADIUS
        rotateSpeed = INITIAL_ROTATION_SPEED
        hue = INITIAL_HUE
        for i in range(NUM_RINGS):
            ring = Ring(self.center, radius, rotateSpeed, RING_SEGMENT_COUNT, hue)
            radius += RING_DISTANCE
            rotateSpeed *= ROTATION_SPEED_MULTIPLIER
            hue += 1 / NUM_RINGS
            self.rings.append(ring)
        self.game_over = False
        self.win = False

    def update(self):
        if self.game_over or self.win:
            for exp in self.particles:
                exp.update()
            self.particles = [exp for exp in self.particles if len(exp.particles) > 0]
            return

        global utils
        global sounds

        utils.world.Step(1.0 / 60.0, 6, 2)

        self.elapsed_time += utils.deltaTime()

        collision_events = len(utils.contactListener.collisions)
        if collision_events > 0:
            self.collision_count += collision_events
            if not self.collision_happened_last_frame:
                sounds.play()
                self.collision_happened_last_frame = True
        else:
            self.collision_happened_last_frame = False
        utils.contactListener.collisions = []

        # Check if the ball has escaped the inner (first) ring.
        if len(self.rings) > 0:
            if self.center.distance_to(self.ball.getPos()) > self.rings[0].radius * 10:
                self.rings[0].destroyFlag = True
                utils.world.DestroyBody(self.rings[0].body)
                self.last_pop_time = self.elapsed_time

        # Process popped rings.
        for ring in self.rings[:]:
            if ring.destroyFlag:
                self.particles += ring.spawParticles()
                self.rings.remove(ring)
                sounds.playDestroySound()

        # If enough time has passed since the last pop, shrink all remaining unpopped rings
        # while maintaining a minimum gap of RING_DISTANCE between each ring.
        if self.last_pop_time is not None and (self.elapsed_time - self.last_pop_time) >= SHRINK_DELAY:
            dt = utils.deltaTime()
            for i, ring in enumerate(self.rings):
                if i == 0:
                    ring.update_shrink(dt, min_allowed=0)
                else:
                    min_allowed = self.rings[i-1].radius + RING_DISTANCE
                    ring.update_shrink(dt, min_allowed=min_allowed)

        for exp in self.particles:
            exp.update()
        self.particles = [exp for exp in self.particles if len(exp.particles) > 0]

    def draw(self, paused=False, timer_value=None):
        global utils
        for ring in self.rings:
            ring.draw(paused=paused)
        if self.ball is not None:
            self.ball.draw()
        for exp in self.particles:
            exp.draw()
        text_surface = self.font.render(f"Bounces: {self.collision_count}", True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=TEXT_POSITION)
        utils.screen.blit(text_surface, text_rect)
        if timer_value is not None:
            display_time = max(timer_value, 0)
            timer_text = f"{display_time:.2f}"
            if timer_value <= 10:
                timer_color = (255, 0, 0)
            elif timer_value > TIMER_DURATION - (TIMER_DURATION / 3):
                timer_color = (0, 255, 0)
            else:
                timer_color = (255, 215, 0)
            timer_surface = self.font.render(timer_text, True, timer_color)
            timer_rect = timer_surface.get_rect(center=TIMER_POSITION)
            utils.screen.blit(timer_surface, timer_rect)
        if self.win:
            big_font = pygame.font.Font(None, 72)
            self.draw_outlined_text("W!", big_font, (0, 0, 0), (255, 255, 255),
                                     (utils.width // 2, utils.height // 2))
        elif self.game_over:
            big_font = pygame.font.Font(None, 72)
            smaller_font = pygame.font.Font(None, 35)
            self.draw_outlined_text("Time's up!", big_font, (0, 0, 0), (255, 255, 255),
                                     (utils.width // 2, utils.height // 2))
            self.draw_outlined_text("Game Over", smaller_font, (0, 0, 0), (255, 255, 255),
                                     (utils.width // 2, utils.height // 1.75))

    def draw_outlined_text(self, text, font, text_color, outline_color, center):
        text_surface = font.render(text, True, text_color)
        outline_surface = font.render(text, True, outline_color)
        for offset in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            pos = (center[0] - text_surface.get_width() // 2 + offset[0],
                   center[1] - text_surface.get_height() // 2 + offset[1])
            utils.screen.blit(outline_surface, pos)
        pos = (center[0] - text_surface.get_width() // 2,
               center[1] - text_surface.get_height() // 2)
        utils.screen.blit(text_surface, pos)

###############################################################################
# Main Loop
###############################################################################
def main():
    global utils
    global sounds

    utils = Utils()
    sounds = Sounds()
    game = Game()

    pause_time_remaining = INITIAL_PAUSE_TIME
    game_timer = TIMER_DURATION

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

        if SOUND_OPTION == 2:
            sounds.update()

        utils.calDeltaTime()
        utils.screen.fill(SCREEN_BACKGROUND_COLOR)

        if pause_time_remaining > 0:
            pause_time_remaining -= utils.deltaTime()
            game.draw(paused=True, timer_value=TIMER_DURATION)
        else:
            if not game.game_over and not game.win:
                if len(game.rings) == 0:
                    game.win = True
                else:
                    game_timer -= utils.deltaTime()
                    if game_timer <= 0 and not game.game_over:
                        if game.ball is not None:
                            ball_pos = game.ball.getPos()
                            explosion = Explosion(ball_pos.x, ball_pos.y, BALL_COLOR)
                            game.particles.append(explosion)
                            utils.world.DestroyBody(game.ball.circle_body)
                            game.ball = None
                            sounds.playDestroySound()
                        game.game_over = True

            if game.game_over or game.win:
                game.draw(paused=False, timer_value=game_timer)
            else:
                game.update()
                game.draw(paused=False, timer_value=game_timer)

        pygame.display.flip()

if __name__ == "__main__":
    main()
