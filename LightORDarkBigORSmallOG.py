import pygame
import random
import math

# Pygame initialization
pygame.init()

# Screen settings
SCREEN_WIDTH = 800  # Width of the simulation window
SCREEN_HEIGHT = 600  # Height of the simulation window
FPS = 60  # Frames per second

# Particle settings
PARTICLE_RADIUS = 5  # Uniform initial radius for all particles
PARTICLE_COLOR = (0, 0, 0)  # Uniform color (green) for all particles
PARTICLE_SPEED = 3  # Uniform speed for all particles
NUM_PARTICLES = 30  # Number of particles in the simulation
PARTICLE_GROWTH = 1  # Amount by which particles grow on collision
MAX_PARTICLE_RADIUS = 50  # Maximum allowed radius for particles

# Customization options
BACKGROUND_COLOR = (0, 0, 0)  # Set the background color here
COLOR_MODE = 'lighter'  # Set to 'darker' or 'lighter' to control particle color changes
SEED = 69  # Change this value for a different sequence of positions

# Set up the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Customizable Particle Simulation")

# Particle class
class Particle:
    """Represents a single particle in the simulation."""
    def __init__(self, x, y, radius, color, vx, vy):
        # Particle properties
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.vx = vx
        self.vy = vy

    def move(self):
        """Updates the particle's position and handles wall collisions."""
        self.x += self.vx
        self.y += self.vy

        # Bounce off the walls
        if self.x - self.radius < 0 or self.x + self.radius > SCREEN_WIDTH:
            self.vx = -self.vx
        if self.y - self.radius < 0 or self.y + self.radius > SCREEN_HEIGHT:
            self.vy = -self.vy

    def draw(self, screen):
        """Draws the particle on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

    def adjust_color(self):
        """
        Adjusts the color of the particle based on its radius.
        Larger particles become darker or lighter depending on COLOR_MODE.
        """
        max_radius = MAX_PARTICLE_RADIUS  # Maximum radius for color adjustment
        min_radius = PARTICLE_RADIUS  # Minimum radius for base color

        # Interpolate the color based on the radius
        factor = min(1, (self.radius - min_radius) / (max_radius - min_radius))  # Clamp to [0, 1]
        r, g, b = PARTICLE_COLOR  # Base color

        if COLOR_MODE == 'darker':
            # Darken the particle color as it grows
            self.color = (
                max(0, int(r * (1 - factor))),
                max(0, int(g * (1 - factor))),
                max(0, int(b * (1 - factor)))
            )
        elif COLOR_MODE == 'lighter':
            # Lighten the particle color as it grows
            self.color = (
                min(255, int(r + (255 - r) * factor)),
                min(255, int(g + (255 - g) * factor)),
                min(255, int(b + (255 - b) * factor))
            )

    def check_collision(self, other):
        """
        Determines if this particle is colliding with another particle.
        """
        dx = self.x - other.x
        dy = self.y - other.y
        distance = math.sqrt(dx**2 + dy**2)
        return distance < self.radius + other.radius  # True if overlapping

    def resolve_collision(self, other):
        """
        Handles the resolution of a collision between two particles.
        Both particles grow in size and adjust their color based on size.
        """
        dx = self.x - other.x
        dy = self.y - other.y
        distance = math.sqrt(dx**2 + dy**2)

        # Prevent division by zero
        if distance == 0:
            return

        # Normalize collision vector
        nx = dx / distance
        ny = dy / distance

        # Relative velocity in the normal direction
        rel_vx = self.vx - other.vx
        rel_vy = self.vy - other.vy
        vel_along_normal = rel_vx * nx + rel_vy * ny

        # Prevent overlapping by acting only if moving toward each other
        if vel_along_normal > 0:
            return

        # Simple elastic collision
        self.vx, other.vx = other.vx, self.vx
        self.vy, other.vy = other.vy, self.vy

        # Grow both particles on collision, but limit their maximum size
        if self.radius < MAX_PARTICLE_RADIUS:
            self.radius += PARTICLE_GROWTH
        if other.radius < MAX_PARTICLE_RADIUS:
            other.radius += PARTICLE_GROWTH

        # Adjust color based on new size
        self.adjust_color()
        other.adjust_color()

# Function to create particles
def create_particles(num_particles, speed, color, seed=None):
    """
    Creates a list of particles with uniform properties and pseudo-random positions.
    """
    if seed is not None:
        random.seed(seed)  # Set the seed for reproducibility

    particles = []
    for _ in range(num_particles):
        # Ensure particles are positioned within bounds
        x = random.randint(PARTICLE_RADIUS, SCREEN_WIDTH - PARTICLE_RADIUS)
        y = random.randint(PARTICLE_RADIUS, SCREEN_HEIGHT - PARTICLE_RADIUS)
        vx = random.choice([-1, 1]) * speed  # Uniform speed with random direction
        vy = random.choice([-1, 1]) * speed
        particles.append(Particle(x, y, PARTICLE_RADIUS, color, vx, vy))
    return particles

# Main simulation function
def main():
    """
    Runs the particle collision simulation.
    """
    # Set up clock for controlling FPS
    clock = pygame.time.Clock()

    # Create particles with uniform speed and color, using a seed for reproducibility
    particles = create_particles(NUM_PARTICLES, PARTICLE_SPEED, PARTICLE_COLOR, seed=SEED)

    # Simulation loop
    running = True
    while running:
        # Fill screen with background color
        screen.fill(BACKGROUND_COLOR)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Exit when the window is closed
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:  # Exit on ESC key
                running = False

        # Update particles
        for i, particle in enumerate(particles):
            particle.move()  # Move particle
            particle.draw(screen)  # Draw particle

            # Check collisions with other particles
            for j in range(i + 1, len(particles)):
                if particle.check_collision(particles[j]):
                    particle.resolve_collision(particles[j])

        # Update display
        pygame.display.flip()

        # Limit frame rate
        clock.tick(FPS)

    # Clean up Pygame
    pygame.quit()

# Run simulation
if __name__ == "__main__":
    main()
