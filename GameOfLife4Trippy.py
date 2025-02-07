import pygame
import random

# ----------------------------
# Settings
# ----------------------------
SCREEN_WIDTH = 432
SCREEN_HEIGHT = 768
RENDER_WIDTH = 1080
RENDER_HEIGHT = 1920

GRID_SIZE = 12
GRID_WIDTH = RENDER_WIDTH // GRID_SIZE
GRID_HEIGHT = RENDER_HEIGHT // GRID_SIZE

FPS = 30  # Keep stable FPS for social media

# Modified "battle" rules:
# More lenient survival and standard birth:
BIRTH_RULE = [3]           # Birth with exactly 3 neighbors
SURVIVAL_RULE = [2, 3, 4]  # Survive if you have 2-4 neighbors (supports larger clusters)

INITIAL_LIVE_CHANCE = 0.3  # More initial particles to have a dense battlefield

# Teams and colors
TEAM_COLORS = {
    "Blue": (0, 100, 255),
    "Green": (0, 200, 0)
}
BACKGROUND_COLOR = (10, 10, 30)

# Fade and transition settings
FADE_SPEED = 0.15       # Faster fade to make transitions more noticeable without flashing
COLOR_BLEND_SPEED = 0.08

# Influence-based conversion:
# If a cell is alive but mostly surrounded by the other team's color,
# it gradually shifts its team color toward that team.
CONVERSION_THRESHOLD = .5002  # If opposite team neighbors outnumber own team neighbors by this factor, convert gradually

# For randomness
SEED = 42

# Font settings
SCORE_FONT_SIZE = 24

pygame.init()
pygame.font.init()
font = pygame.font.SysFont("Arial", SCORE_FONT_SIZE)

def initialize_seed(seed):
    random.seed(seed)

def create_grid():
    """Initialize grid with random live/dead states and random teams."""
    grid = []
    for y in range(GRID_HEIGHT):
        row = []
        for x in range(GRID_WIDTH):
            alive = random.random() < INITIAL_LIVE_CHANCE
            team = random.choice(["Blue", "Green"]) if alive else None
            state_factor = 1.0 if alive else 0.0
            color = TEAM_COLORS[team] if alive else BACKGROUND_COLOR
            cell = {
                "alive": alive,
                "team": team,
                "color_current": color,
                "color_target": color,
                "state_factor_current": state_factor,
                "state_factor_target": state_factor
            }
            row.append(cell)
        grid.append(row)
    return grid

NEIGHBOR_OFFSETS = [(-1, -1), (0, -1), (1, -1),
                    (-1, 0),           (1, 0),
                    (-1, 1),  (0, 1),  (1, 1)]

def count_neighbors(grid, x, y):
    """Count alive neighbors and their team distribution."""
    alive_count = 0
    team_counts = {"Blue": 0, "Green": 0}
    for dx, dy in NEIGHBOR_OFFSETS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
            neigh = grid[ny][nx]
            if neigh["alive"]:
                alive_count += 1
                if neigh["team"] is not None:
                    team_counts[neigh["team"]] += 1
    return alive_count, team_counts

def determine_team_on_birth(team_counts):
    """Determine team color for a newly born cell based on majority neighbors."""
    blue_n = team_counts["Blue"]
    green_n = team_counts["Green"]
    if blue_n > green_n:
        return "Blue"
    elif green_n > blue_n:
        return "Green"
    else:
        return random.choice(["Blue", "Green"])

def next_generation(grid):
    """Compute the next generation of the grid with battle-focused rules."""
    new_grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            alive_count, team_counts = count_neighbors(grid, x, y)

            was_alive = cell["alive"]
            my_team = cell["team"]

            # Apply modified "Game of Life" rules
            if was_alive:
                will_live = (alive_count in SURVIVAL_RULE)
            else:
                will_live = (alive_count in BIRTH_RULE)

            if will_live:
                # Determine team
                if was_alive:
                    team = my_team
                else:
                    team = determine_team_on_birth(team_counts)

                color_target = TEAM_COLORS[team]
                state_factor_target = 1.0

            else:
                team = None
                color_target = BACKGROUND_COLOR
                state_factor_target = 0.0

            # Prepare the new cell data
            new_cell = {
                "alive": will_live,
                "team": team,
                "color_current": cell["color_current"],
                "color_target": color_target,
                "state_factor_current": cell["state_factor_current"],
                "state_factor_target": state_factor_target
            }

            # Introduce gradual team conversion:
            # If cell is alive and is heavily outnumbered by the other team, shift team.
            if will_live and team is not None:
                opp_team = "Blue" if team == "Green" else "Green"
                own_count = team_counts[team]
                opp_count = team_counts[opp_team]

                # If overwhelmed by opposite team:
                if opp_count > own_count * CONVERSION_THRESHOLD:
                    # Gradually shift target color toward opposite team color
                    # We won't change team instantly, just the color target will blend.
                    # After a few generations of being overwhelmed, color and eventually team will appear to shift.
                    # After a certain degree of shift, we can actually flip the team to maintain consistency.
                    # For simplicity, just blend the color target towards the opponent.
                    new_cell["team"] = team  # keep same team label for now
                    # Blend the color target halfway:
                    rt, gt, bt = TEAM_COLORS[opp_team]
                    # Average with current target to inch towards the opposing color
                    ct = new_cell["color_target"]
                    new_cell["color_target"] = ((ct[0]+rt)/2, (ct[1]+gt)/2, (ct[2]+bt)/2)

                    # Optional: If the color is close to the opponent's color, switch team
                    if color_distance(new_cell["color_target"], TEAM_COLORS[opp_team]) < 20:
                        new_cell["team"] = opp_team

            new_grid[y][x] = new_cell

    return new_grid

def color_distance(c1, c2):
    return abs(c1[0]-c2[0]) + abs(c1[1]-c2[1]) + abs(c1[2]-c2[2])

def interpolate_values(cell):
    """Interpolate the cell's current values toward their targets for smooth transitions."""
    # Interpolate state factor (fading)
    sc = cell["state_factor_current"]
    st = cell["state_factor_target"]
    if abs(sc - st) > FADE_SPEED:
        sc += FADE_SPEED if sc < st else -FADE_SPEED
    else:
        sc = st
    cell["state_factor_current"] = sc

    # Interpolate color
    cc = cell["color_current"]
    ct = cell["color_target"]
    def blend(c, t):
        diff = t - c
        return c + diff * COLOR_BLEND_SPEED

    r_new = blend(cc[0], ct[0])
    g_new = blend(cc[1], ct[1])
    b_new = blend(cc[2], ct[2])

    cell["color_current"] = (r_new, g_new, b_new)

def update_visuals(grid):
    """Perform interpolation of colors and states for smooth transitions."""
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            interpolate_values(grid[y][x])

def draw_grid(surface, grid):
    """Draw the grid to the surface."""
    surface.fill(BACKGROUND_COLOR)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            factor = cell["state_factor_current"]
            if factor > 0:
                # Increase size for more visual impact
                color = (int(cell["color_current"][0]),
                         int(cell["color_current"][1]),
                         int(cell["color_current"][2]))
                size = int((GRID_SIZE // 2) * factor + (GRID_SIZE // 2))
                cx = x * GRID_SIZE + GRID_SIZE // 2
                cy = y * GRID_SIZE + GRID_SIZE // 2
                pygame.draw.circle(surface, color, (cx, cy), size)

def calculate_scores(grid):
    """Calculate the number of alive cells for each team."""
    scores = {"Blue": 0, "Green": 0}
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            if cell["alive"] and cell["team"] is not None:
                scores[cell["team"]] += 1
    return scores

def render_text_with_border(screen, text, font, color, x, y):
    black = (0, 0, 0)
    offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
    for ox, oy in offsets:
        border_surface = font.render(text, True, black)
        screen.blit(border_surface, (x + ox, y + oy))
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def main():
    initialize_seed(SEED)

    grid = create_grid()
    clock = pygame.time.Clock()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Dynamic Particle Battle")
    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
               event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # Compute next generation
        grid = next_generation(grid)

        # Smooth transitions
        update_visuals(grid)

        # Draw on the high-res surface
        draw_grid(render_surface, grid)

        # Scale down
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Scores
        scores = calculate_scores(grid)
        render_text_with_border(screen, f"Blue: {scores['Blue']}", font, TEAM_COLORS["Blue"], 10, 10)
        render_text_with_border(screen, f"Green: {scores['Green']}", font, TEAM_COLORS["Green"], 10, 40)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
