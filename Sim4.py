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
SEED = 92

# Screen settings
SCREEN_WIDTH = 432       # Display window width
SCREEN_HEIGHT = 768      # Display window height
SCREEN_BACKGROUND_COLOR = (0, 0, 29)

# Physics and Pygame updates
FRAMERATE = 60
PPM = 10.0  # Pixels per meter

# Gravity rotates around to "bounce"
GRAVITY_MAG = 70        # Gravity magnitude
GRAVITY_ROT_SPEED = 0.0005  # How fast gravity rotates

# Ball settings
BALL_RADIUS = 1
BALL_COLOR = (255, 255, 255)

# Rings settings
NUM_RINGS = 14
INITIAL_RING_RADIUS = 8
RING_DISTANCE = 2.5       # You can change this to increase/decrease ring spacing
INITIAL_ROTATION_SPEED = 1.50
ROTATION_SPEED_MULTIPLIER = 1.003
INITIAL_HUE = 0
RING_LINE_THICKNESS = 8

# For the ring shape logic in the code:
RING_SEGMENT_COUNT = 50
TRIANGLE_SIZE = 3
SQUARE_SIZE = 4

# NEW VARIABLE: the max angle (0..360) where edges are drawn. The rest is the gap.
CIRCLE_GAP_END_ANGLE = 297.0

# Explosion / Particle settings
PARTICLE_COUNT = 20
PARTICLE_SIZE_MIN = 0.5
PARTICLE_SIZE_MAX = 2
PARTICLE_ANGLE_MIN = 0
PARTICLE_ANGLE_MAX = 360
PARTICLE_SPEED_MIN = 0.1
PARTICLE_SPEED_MAX = 1
PARTICLE_LIFE_MIN = 100
PARTICLE_LIFE_MAX = 1000

# Initial pause at the start of the game (in seconds)
INITIAL_PAUSE_TIME = 3.0

# SOUND AND VOLUME SETTINGS
COLLISION_VOLUME = 0.69
DESTROY_VOLUME = 0.35
DESTROY_SOUND_FILE = "assets/Mustard.mp3"
COLLISION_SOUND_FILES = [
    "assets/(1).wav",
    "assets/(2).wav",
    "assets/(3).wav"
]
COLLISION_SOUND2 = "tvoffInstra.wav"

# NEW SOUND OPTION SETTINGS
SOUND_OPTION = 1  # 1: current behavior, 2: new snippet-based behavior
SNIPPET_DURATION = 0.5  # snippet duration in seconds (adjust as needed)
COLLISION_OVERLAP_BUFFER = 0.01  # collision overlap buffer in seconds (10 ms)

# TEXT RENDER SETTINGS
TEXT_COLOR = (255, 255, 255)
TEXT_POSITION = (SCREEN_WIDTH // 2, 70)  # Centered horizontally, 80px from top

# TIMER SETTINGS
TIMER_DURATION = 30.0  # Default timer length in seconds (can be changed)
TIMER_POSITION = (SCREEN_WIDTH // 2, 37)  # Timer displayed above bounce count

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
        # We'll start gravity at (0, -GRAVITY_MAG), but we’ll rotate it each frame:
        self.world = b2World(gravity=(0, -GRAVITY_MAG), doSleep=True)

        self.contactListener = MyContactListener()
        self.world.contactListener = self.contactListener

        # We'll keep track of an angle for gravity so that it "bounces around"
        self.gravityAngle = -math.pi / 2  # start direction (straight down)

    def to_Pos(self, pos):
        """Convert from Box2D to Pygame coordinates."""
        return (pos[0] * self.PPM, self.height - (pos[1] * self.PPM))

    def from_Pos(self, pos):
        """Convert from Pygame to Box2D coordinates."""
        return (pos[0] / self.PPM, (self.height - pos[1]) / self.PPM)

    def calDeltaTime(self):
        # calculate deltaTime
        t = self.clock.tick(FRAMERATE)
        self.dt = t / 1000

        # Rotate gravity so it moves around in a circle
        self.gravityAngle += GRAVITY_ROT_SPEED * self.dt
        gx = GRAVITY_MAG * math.cos(self.gravityAngle)
        gy = GRAVITY_MAG * math.sin(self.gravityAngle)
        self.world.gravity = (gx, gy)

    def deltaTime(self):
        return self.dt

    def hueToRGB(self, hue):
        """
        Convert HSV (with hue in [0,1], full saturation, full brightness)
        to an RGB color. This cycles through all possible hues.
        """
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        # Scale RGB values to 0-255 range
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
        # Size
        self.radius = random.uniform(PARTICLE_SIZE_MIN, PARTICLE_SIZE_MAX)

        # Direction and speed
        angle = random.uniform(PARTICLE_ANGLE_MIN, PARTICLE_ANGLE_MAX)
        speed = random.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)

        self.x = x
        self.y = y
        self.color = color
        self.vel_x = math.cos(math.radians(angle)) * speed
        self.vel_y = math.sin(math.radians(angle)) * speed

        # Lifetime
        self.life = random.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX)

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.life -= 1

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.radius))

class Explosion:
    def __init__(self, x, y, color):
        # Create particles
        self.particles = []
        COLORS = [color]  # can expand if desired
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
        """
        This draws the ring edges for angles [0..CIRCLE_GAP_END_ANGLE].
        The rest is left open, creating the gap in the ring.
        """
        if self.size == RING_SEGMENT_COUNT:
            for i in range(self.size):
                angle = i * (360 / self.size)
                # Only draw edges if the angle is within 0..CIRCLE_GAP_END_ANGLE
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

    def draw(self, paused=False):
        global utils
        # Only update the hue/rotation if not paused
        if not paused:
            self.hue = (self.hue + utils.deltaTime() / 5) % 1
            self.body.angle += self.rotateDir * utils.deltaTime()

        self.color = utils.hueToRGB(self.hue)
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
        # Destroy sound remains unchanged
        self.destroySound = pygame.mixer.Sound(DESTROY_SOUND_FILE)
        self.destroySound.set_volume(DESTROY_VOLUME)

        if SOUND_OPTION == 1:
            # Option 1: current behavior using multiple collision sound files
            self.sounds = [pygame.mixer.Sound(f) for f in COLLISION_SOUND_FILES]
            for s in self.sounds:
                s.set_volume(COLLISION_VOLUME)
            self.i = 0
        elif SOUND_OPTION == 2:
            # Option 2: new snippet-based behavior with one collision sound file
            self.collision_file = COLLISION_SOUND2
            pygame.mixer.music.load(self.collision_file)
            self.collisionSoundLength = pygame.mixer.Sound(self.collision_file).get_length()
            pygame.mixer.music.set_volume(COLLISION_VOLUME)
            self.current_pos = 0.0  # track current play position (in seconds)
            self.last_collision_time = -10000  # in milliseconds; ensures first collision plays
            # Custom event for stopping sound
            self.STOP_SOUND_EVENT = pygame.USEREVENT + 1

    def play(self):
        if SOUND_OPTION == 1:
            # Option 1: current behavior
            for sound in self.sounds:
                sound.stop()
            sound = self.sounds[self.i]
            sound.play()
            self.i += 1
            if self.i >= len(self.sounds):
                self.i = 0
        elif SOUND_OPTION == 2:
            # Option 2: new snippet-based behavior
            current_time = pygame.time.get_ticks()  # current time in milliseconds
            # If collision occurs within the overlap buffer, do not play
            if (current_time - self.last_collision_time) < (COLLISION_OVERLAP_BUFFER * 1000):
                return

            # Stop any currently playing sound
            pygame.mixer.music.stop()
            
            self.last_collision_time = current_time
            
            # Calculate remaining time and adjust duration if needed
            remaining_time = self.collisionSoundLength - self.current_pos
            duration = min(SNIPPET_DURATION, remaining_time)
            
            # Play the snippet from current position
            pygame.mixer.music.play(start=self.current_pos)
            
            # Schedule stop event
            pygame.time.set_timer(self.STOP_SOUND_EVENT, int(duration * 1000))
            # We'll handle the stop and position update in the main loop

    def playDestroySound(self):
        self.destroySound.play()

    def handle_events(self):
        # Handle custom sound stop event
        for event in pygame.event.get(self.STOP_SOUND_EVENT):
            if event.type == self.STOP_SOUND_EVENT:
                pygame.mixer.music.stop()
                pygame.time.set_timer(self.STOP_SOUND_EVENT, 0)  # Clear the timer
                self.current_pos += SNIPPET_DURATION
                if self.current_pos >= self.collisionSoundLength:
                    self.current_pos = 0.0  # Reset to start if we reach the end

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

        # Keep track of collisions/bounces
        self.collision_count = 0
        # Create a font to display the collision count and timer
        self.font = pygame.font.Font(None, 36)

        # Create rings based on configurable variables
        radius = INITIAL_RING_RADIUS
        rotateSpeed = INITIAL_ROTATION_SPEED
        hue = INITIAL_HUE

        for i in range(NUM_RINGS):
            ring = Ring(self.center, radius, rotateSpeed, RING_SEGMENT_COUNT, hue)
            radius += RING_DISTANCE           # adjustable gap between rings
            rotateSpeed *= ROTATION_SPEED_MULTIPLIER
            hue += 1 / NUM_RINGS
            self.rings.append(ring)

        # Game over flag (for ball pop) and win flag (all rings broken)
        self.game_over = False
        self.win = False

    def update(self):
        """
        Update the physics world and game state.
        """
        # If game over or win, skip normal updates and only update explosions
        if self.game_over or self.win:
            for exp in self.particles:
                exp.update()
            self.particles = [exp for exp in self.particles if len(exp.particles) > 0]
            return

        global utils
        global sounds

        utils.world.Step(1.0 / 60.0, 6, 2)

        # Check collisions
        if utils.contactListener:
            collision_events = len(utils.contactListener.collisions)
            if collision_events > 0:
                self.collision_count += collision_events
                sounds.play()
            utils.contactListener.collisions = []

        # Ring destruction logic: if ball is outside the ring radius, break the ring
        if len(self.rings) > 0:
            if self.center.distance_to(self.ball.getPos()) > self.rings[0].radius * 10:
                self.rings[0].destroyFlag = True
                utils.world.DestroyBody(self.rings[0].body)

        # Spawn ring explosion if a ring is destroyed
        for ring in self.rings:
            if ring.destroyFlag:
                self.particles += ring.spawParticles()
                self.rings.remove(ring)
                sounds.playDestroySound()

        # Update ring explosion particles
        for exp in self.particles:
            exp.update()
        self.particles = [exp for exp in self.particles if len(exp.particles) > 0]

    def draw(self, paused=False, timer_value=None):
        """
        Draw the rings, ball, particle explosions, timer and collision count.
        If paused=True, the rings won't rotate or change color.
        """
        global utils
        # Draw rings
        for ring in self.rings:
            ring.draw(paused=paused)
        # Draw ball if it hasn't been popped
        if self.ball is not None:
            self.ball.draw()
        # Draw explosions
        for exp in self.particles:
            exp.draw()

        # Render the collision count in the center-top
        text_surface = self.font.render(f"Bounces: {self.collision_count}", True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=TEXT_POSITION)
        utils.screen.blit(text_surface, text_rect)

        # Draw timer above bounce count
        if timer_value is not None:
            display_time = max(timer_value, 0)
            timer_text = f"{display_time:.2f}"
            if timer_value <= 10:
                timer_color = (255, 0, 0)  # red
            elif timer_value > TIMER_DURATION - (TIMER_DURATION / 3):
                timer_color = (0, 255, 0)  # green
            else:
                timer_color = (255, 215, 0)  # golden yellow
            timer_surface = self.font.render(timer_text, True, timer_color)
            timer_rect = timer_surface.get_rect(center=TIMER_POSITION)
            utils.screen.blit(timer_surface, timer_rect)

        # Display win or game over message
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
        """
        Draws text with an outline.
        """
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

    # Pause timer
    pause_time_remaining = INITIAL_PAUSE_TIME
    # Game timer starts after the pause
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
            # Handle sound events
            if SOUND_OPTION == 2:
                sounds.handle_events()

        utils.calDeltaTime()
        utils.screen.fill(SCREEN_BACKGROUND_COLOR)

        if pause_time_remaining > 0:
            pause_time_remaining -= utils.deltaTime()
            game.draw(paused=True, timer_value=TIMER_DURATION)
        else:
            # If not already game over or win, check if all rings are broken
            if not game.game_over and not game.win:
                if len(game.rings) == 0:
                    # Win condition: freeze timer and set win flag
                    game.win = True
                else:
                    game_timer -= utils.deltaTime()
                    if game_timer <= 0 and not game.game_over:
                        # Timer ran out: pop the ball with explosion and sound
                        if game.ball is not None:
                            ball_pos = game.ball.getPos()
                            explosion = Explosion(ball_pos.x, ball_pos.y, BALL_COLOR)
                            game.particles.append(explosion)
                            utils.world.DestroyBody(game.ball.circle_body)
                            game.ball = None
                            sounds.playDestroySound()
                        game.game_over = True

            if game.game_over or game.win:
                # Freeze timer display
                game.draw(paused=False, timer_value=game_timer)
            else:
                game.update()
                game.draw(paused=False, timer_value=game_timer)

        pygame.display.flip()

if __name__ == "__main__":
    main()