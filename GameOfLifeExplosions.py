import pygame
import random

# Screen and rendering settings
SCREEN_WIDTH = 432
SCREEN_HEIGHT = 768
RENDER_WIDTH = 1080
RENDER_HEIGHT = 1920
FPS = 30

# Grid and cell settings
GRID_SIZE = 12
CELL_MAX_STATE = 20
INITIAL_LIVE_CHANCE = 0.04
DECAY_PROBABILITY = 0.5
COLOR_CHANGE_RATE = 0.05
EXPLOSION_THRESHOLD = 1000  # Minimum size for a cluster to trigger a shockwave
EXPLOSION_RADIUS = 1  # Radius (in cells) of the shockwave effect

# Seed for reproducibility
SEED = 42

# Team settings
TEAM_COLORS = {"Red": (255, 0, 0), "Blue": (0, 0, 255)}
MIXED_COLOR = (180, 0, 180)
BACKGROUND_COLOR = (10, 10, 30)

# Rules
BIRTH_THRESHOLD = 3
STABILITY_RANGE = (2, 4)

# Precompute neighbor offsets
NEIGHBOR_OFFSETS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

# Set up the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("War of Colors")

# High-res surface
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

GRID_WIDTH = RENDER_WIDTH // GRID_SIZE
GRID_HEIGHT = RENDER_HEIGHT // GRID_SIZE


def initialize_seed(seed):
    """Set random seed."""
    random.seed(seed)


def create_grid():
    """Initialize the grid with random team cells."""
    grid = [[{"state": random.randint(0, CELL_MAX_STATE) if random.random() < INITIAL_LIVE_CHANCE else 0,
              "team": random.choice(["Red", "Blue"]),
              "exploded": False} for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    return grid


def count_team_neighbors(grid, x, y):
    """Count the number of neighbors for each team."""
    team_counts = {"Red": 0, "Blue": 0}
    for dx, dy in NEIGHBOR_OFFSETS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and grid[ny][nx]["state"] > 0:
            team_counts[grid[ny][nx]["team"]] += 1
    return team_counts


def detect_clusters(grid):
    """Detect large clusters of cells for each team."""
    clusters = {"Red": [], "Blue": []}
    visited = [[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    def dfs(x, y, team, cluster):
        if visited[y][x] or grid[y][x]["team"] != team or grid[y][x]["state"] == 0:
            return
        visited[y][x] = True
        cluster.append((x, y))
        for dx, dy in NEIGHBOR_OFFSETS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                dfs(nx, ny, team, cluster)

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            if grid[y][x]["state"] > 0 and not visited[y][x]:
                team = grid[y][x]["team"]
                cluster = []
                dfs(x, y, team, cluster)
                if cluster:
                    clusters[team].append(cluster)

    return clusters


def trigger_shockwaves(grid, clusters):
    """Trigger shockwaves for large clusters."""
    for team, team_clusters in clusters.items():
        for cluster in team_clusters:
            if len(cluster) >= EXPLOSION_THRESHOLD:
                # Trigger shockwave
                for cx, cy in cluster:
                    grid[cy][cx]["exploded"] = True  # Mark cell as exploded
                    for dx, dy in NEIGHBOR_OFFSETS:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and grid[ny][nx]["state"] > 0:
                            # Decay cells in the explosion radius
                            grid[ny][nx]["state"] = max(0, grid[ny][nx]["state"] - 5)

def draw_grid(surface, grid):
    """Draw the grid."""
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            if cell["state"] > 0:
                color = get_color(cell)
                size = int(GRID_SIZE * (0.5 + 0.5 * (cell["state"] / CELL_MAX_STATE)))
                cx = x * GRID_SIZE + GRID_SIZE // 2
                cy = y * GRID_SIZE + GRID_SIZE // 2
                pygame.draw.circle(surface, color, (cx, cy), size)


def get_color(cell):
    """Get the color of a cell based on team and state."""
    if cell["state"] == 0:
        return BACKGROUND_COLOR
    base_color = TEAM_COLORS.get(cell["team"], MIXED_COLOR)
    fade_factor = cell["state"] / CELL_MAX_STATE
    return tuple(int(c * fade_factor) for c in base_color)



def update_grid(grid):
    """Evolve the grid based on team influence and shockwaves."""
    new_grid = [[{"state": 0, "team": None, "exploded": False} for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    # Detect clusters and trigger shockwaves
    clusters = detect_clusters(grid)
    trigger_shockwaves(grid, clusters)

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            team_counts = count_team_neighbors(grid, x, y)
            total_neighbors = team_counts["Red"] + team_counts["Blue"]

            # Decide the dominant team based on majority
            dominant_team = None
            if team_counts["Red"] > team_counts["Blue"]:
                dominant_team = "Red"
            elif team_counts["Blue"] > team_counts["Red"]:
                dominant_team = "Blue"

            # Cell behavior
            if cell["state"] > 0:  # Active cell
                if not cell["exploded"]:  # Only update non-exploded cells
                    if STABILITY_RANGE[0] <= total_neighbors <= STABILITY_RANGE[1]:
                        new_grid[y][x] = {"state": min(cell["state"] + 1, CELL_MAX_STATE),
                                          "team": cell["team"],
                                          "exploded": False}
                    else:
                        new_grid[y][x] = {"state": max(cell["state"] - 1, 0),
                                          "team": cell["team"],
                                          "exploded": False}
                else:
                    new_grid[y][x] = {"state": max(0, cell["state"] - 5), "team": cell["team"], "exploded": False}
            elif total_neighbors == BIRTH_THRESHOLD and dominant_team:  # Birth
                new_grid[y][x] = {"state": 1, "team": dominant_team, "exploded": False}

            # Decay
            if random.random() < DECAY_PROBABILITY and new_grid[y][x]["state"] > 0:
                new_grid[y][x]["state"] -= 1

    return new_grid


def main():
    """Main simulation."""
    initialize_seed(SEED)
    grid = create_grid()
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        grid = update_grid(grid)

        # Draw grid
        render_surface.fill(BACKGROUND_COLOR)
        draw_grid(render_surface, grid)

        # Scale and display
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
