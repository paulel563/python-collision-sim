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
SEED = 42

# Screen settings
SCREEN_WIDTH = 432       # Display window width
SCREEN_HEIGHT = 768      # Display window height
SCREEN_BACKGROUND_COLOR = (0, 0, 29)

# Physics and Pygame updates
FRAMERATE = 60
PPM = 10.0  # Pixels per meter

# Gravity rotates around to "bounce"
GRAVITY_MAG = 20         # Gravity magnitude
GRAVITY_ROT_SPEED = 0.005  # How fast gravity rotates

# Ball settings
BALL_RADIUS = 1
BALL_COLOR = (255, 255, 255)

# Rings settings
NUM_RINGS = 12
INITIAL_RING_RADIUS = 5
RING_DISTANCE = 1.4       # You can change this to increase/decrease ring spacing
INITIAL_ROTATION_SPEED = 1
ROTATION_SPEED_MULTIPLIER = 1.04
INITIAL_HUE = 0
RING_LINE_THICKNESS = 4

# For the ring shape logic in the code:
RING_SEGMENT_COUNT = 50
TRIANGLE_SIZE = 3
SQUARE_SIZE = 4

# NEW VARIABLE: the max angle (0..360) where edges are drawn. The rest is the gap.
CIRCLE_GAP_END_ANGLE = 310.0

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
        if self.size == RING_SEGMENT_COUNT:  # was 50
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
        # Example asset references (ensure these files exist in your assets folder)
        self.destroySound = pygame.mixer.Sound("assets/pickupCoin.wav")

        self.sounds = [
            pygame.mixer.Sound("assets/(1).wav"),
            pygame.mixer.Sound("assets/(2).wav"),
            pygame.mixer.Sound("assets/(3).wav")
        ]
        self.i = 0

    def play(self):
        # stop all sound
        for sound in self.sounds:
            sound.stop()
        # play sound
        sound = self.sounds[self.i]
        sound.play()
        self.i += 1
        if self.i >= len(self.sounds):
            self.i = 0

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

    def update(self):
        """
        Update the physics world and game state.
        """
        global utils
        global sounds

        utils.world.Step(1.0 / 60.0, 6, 2)

        # check collisions
        if utils.contactListener:
            for bodyA, bodyB in utils.contactListener.collisions:
                sounds.play()
                break
            utils.contactListener.collisions = []

        # ring destruction logic
        if len(self.rings) > 0:
            # if ball is outside the ring radius => destroy ring
            if self.center.distance_to(self.ball.getPos()) > self.rings[0].radius * 10:
                self.rings[0].destroyFlag = True
                utils.world.DestroyBody(self.rings[0].body)

        # spawn ring explosion if destroyed
        for ring in self.rings:
            if ring.destroyFlag:
                self.particles += ring.spawParticles()
                self.rings.remove(ring)
                sounds.playDestroySound()

        # update ring explosion particles
        for exp in self.particles:
            exp.update()
            if len(exp.particles) == 0:
                self.particles.remove(exp)

    def draw(self, paused=False):
        """
        Draw the rings, ball, and particle explosions.
        If paused=True, the rings won't rotate or change color.
        """
        global utils
        for ring in self.rings:
            ring.draw(paused=paused)
        self.ball.draw()

        for exp in self.particles:
            exp.draw()

###############################################################################
# Main Loop
###############################################################################
def main():
    global utils
    global sounds

    # Create global utilities and sound objects
    utils = Utils()
    sounds = Sounds()

    game = Game()

    # Pause timer
    pause_time_remaining = INITIAL_PAUSE_TIME

    while True:
        # Check events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            # Exit on ESC
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

        # Calculate deltaTime (also rotates gravity)
        utils.calDeltaTime()

        # Fill background
        utils.screen.fill(SCREEN_BACKGROUND_COLOR)

        # If we still have pause time, reduce it but skip game updates
        if pause_time_remaining > 0:
            pause_time_remaining -= utils.deltaTime()
            # Draw everything in a "paused" state
            game.draw(paused=True)
        else:
            # Otherwise update and draw as normal
            game.update()
            game.draw(paused=False)

        pygame.display.flip()

if __name__ == "__main__":
    main()
