import pygame
import random
import math

# Pygame initialization
pygame.init()

# Screen and rendering settings
SCREEN_WIDTH = 360  # Window display width
SCREEN_HEIGHT = 640  # Window display height
RENDER_WIDTH = 1080  # Render resolution width (e.g., Full HD)
RENDER_HEIGHT = 1920  # Render resolution height (e.g., Full HD)
FPS = 60

# Particle settings
PARTICLE_RADIUS = 5  # Initial radius for all particles
PARTICLE_COLOR = (0, 0, 0)  # Uniform color (green) for all particles
PARTICLE_SPEED = 2  # Uniform speed for all particles
NUM_PARTICLES = 1000  # Number of particles in the simulation
PARTICLE_GROWTH = 1  # Growth rate upon collision
MAX_PARTICLE_RADIUS = 15  # Maximum radius for particles

# Customization options
BACKGROUND_COLOR = (0, 0, 0)  # Background color
COLOR_MODE = 'lighter'  # 'darker' or 'lighter' to adjust particle color changes
SEED = 42  # Seed for reproducibility

# Grid settings
GRID_SIZE = 50  # Size of grid cells for spatial partitioning

# Set up the screen and high-resolution render surface
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Optimized Particle Simulation")
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))


# Particle class
class Particle:
    """Represents a single particle in the simulation."""
    def __init__(self, x, y, radius, color, vx, vy):
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

        # Bounce off walls
        if self.x - self.radius < 0 or self.x + self.radius > RENDER_WIDTH:
            self.vx = -self.vx
        if self.y - self.radius < 0 or self.y + self.radius > RENDER_HEIGHT:
            self.vy = -self.vy

    def draw(self, surface):
        """Draws the particle on the given surface."""
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

    def adjust_color(self):
        """Adjusts the color of the particle based on its radius."""
        max_radius = MAX_PARTICLE_RADIUS
        min_radius = PARTICLE_RADIUS
        factor = min(1, (self.radius - min_radius) / (max_radius - min_radius))

        r, g, b = PARTICLE_COLOR
        if COLOR_MODE == 'darker':
            self.color = (
                max(0, int(r * (1 - factor))),
                max(0, int(g * (1 - factor))),
                max(0, int(b * (1 - factor)))
            )
        elif COLOR_MODE == 'lighter':
            self.color = (
                min(255, int(r + (255 - r) * factor)),
                min(255, int(g + (255 - g) * factor)),
                min(255, int(b + (255 - b) * factor))
            )

    def check_collision(self, other):
        """Checks if this particle is colliding with another particle."""
        dx = self.x - other.x
        dy = self.y - other.y
        distance_squared = dx**2 + dy**2
        return distance_squared < (self.radius + other.radius) ** 2

    def resolve_collision(self, other):
        """Handles collision resolution between two particles."""
        if self.radius < MAX_PARTICLE_RADIUS:
            self.radius += PARTICLE_GROWTH
        if other.radius < MAX_PARTICLE_RADIUS:
            other.radius += PARTICLE_GROWTH

        self.adjust_color()
        other.adjust_color()


def create_particles(num_particles, speed, color, seed=None):
    """Creates particles with random positions and velocities."""
    if seed is not None:
        random.seed(seed)

    particles = []
    for _ in range(num_particles):
        x = random.randint(PARTICLE_RADIUS, RENDER_WIDTH - PARTICLE_RADIUS)
        y = random.randint(PARTICLE_RADIUS, RENDER_HEIGHT - PARTICLE_RADIUS)
        vx = random.choice([-1, 1]) * speed
        vy = random.choice([-1, 1]) * speed
        particles.append(Particle(x, y, PARTICLE_RADIUS, color, vx, vy))
    return particles


def spatial_partitioning(particles):
    """Organizes particles into a spatial grid for efficient collision detection."""
    grid = {}
    for particle in particles:
        grid_x = int(particle.x // GRID_SIZE)
        grid_y = int(particle.y // GRID_SIZE)
        cell = (grid_x, grid_y)
        if cell not in grid:
            grid[cell] = []
        grid[cell].append(particle)
    return grid


def check_collisions(grid):
    """Checks and resolves collisions using spatial partitioning."""
    for cell, cell_particles in grid.items():
        for i, particle in enumerate(cell_particles):
            for j in range(i + 1, len(cell_particles)):
                if particle.check_collision(cell_particles[j]):
                    particle.resolve_collision(cell_particles[j])

        neighbors = [
            (cell[0] - 1, cell[1]), (cell[0] + 1, cell[1]),
            (cell[0], cell[1] - 1), (cell[0], cell[1] + 1)
        ]
        for neighbor in neighbors:
            if neighbor in grid:
                for particle in cell_particles:
                    for other in grid[neighbor]:
                        if particle.check_collision(other):
                            particle.resolve_collision(other)


def main():
    """Main simulation function."""
    particles = create_particles(NUM_PARTICLES, PARTICLE_SPEED, PARTICLE_COLOR, seed=SEED)
    clock = pygame.time.Clock()
    running = True

    while running:
        render_surface.fill(BACKGROUND_COLOR)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        grid = spatial_partitioning(particles)
        check_collisions(grid)

        for particle in particles:
            particle.move()
            particle.draw(render_surface)

        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
