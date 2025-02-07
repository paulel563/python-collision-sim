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

FPS = 60  # Stable for social media

# Modified rules to keep more particles alive and battling:
BIRTH_RULE = [3]           # Birth with 3 neighbors
SURVIVAL_RULE = [2, 3, 4]  # Survive with 2-4 neighbors

INITIAL_LIVE_CHANCE = 0.055

TEAM_COLORS = {
    "Blue": (0, 100, 255),
    "Green": (0, 200, 0)
}
BACKGROUND_COLOR = (10, 10, 30)

FADE_SPEED = 0.15
COLOR_BLEND_SPEED = 0.1

# Make conversions more aggressive
CONVERSION_THRESHOLD = 2

# Random perturbations:
RANDOM_TOGGLE_RATE = 0.000005  # 0.1% chance per cell per frame
COLOR_DRIFT_CHANCE = 0.000005

SEED = 69
SCORE_FONT_SIZE = 24

# Timing variables:
START_DELAY_SECONDS = 2      # Show initial state for 2 seconds
CALM_DOWN_TIME_SECONDS = 10  # After 20 seconds, no more toggling/drifting

pygame.init()
pygame.font.init()
font = pygame.font.SysFont("Arial", SCORE_FONT_SIZE)

def initialize_seed(seed):
    random.seed(seed)

def create_grid():
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
    blue_n = team_counts["Blue"]
    green_n = team_counts["Green"]
    if blue_n > green_n:
        return "Blue"
    elif green_n > blue_n:
        return "Green"
    else:
        return random.choice(["Blue", "Green"])

def color_distance(c1, c2):
    return abs(c1[0]-c2[0]) + abs(c1[1]-c2[1]) + abs(c1[2]-c2[2])

def next_generation(grid, chaos_enabled):
    new_grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            alive_count, team_counts = count_neighbors(grid, x, y)

            was_alive = cell["alive"]
            my_team = cell["team"]

            # Apply rules
            if was_alive:
                will_live = (alive_count in SURVIVAL_RULE)
            else:
                will_live = (alive_count in BIRTH_RULE)

            if will_live:
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

            new_cell = {
                "alive": will_live,
                "team": team,
                "color_current": cell["color_current"],
                "color_target": color_target,
                "state_factor_current": cell["state_factor_current"],
                "state_factor_target": state_factor_target
            }

            # Team conversion if overwhelmed
            if will_live and team is not None:
                opp_team = "Blue" if team == "Green" else "Green"
                own_count = team_counts[team]
                opp_count = team_counts[opp_team]

                if opp_count > own_count * CONVERSION_THRESHOLD:
                    # Blend color target towards opponent color
                    rt, gt, bt = TEAM_COLORS[opp_team]
                    ct = new_cell["color_target"]
                    new_cell["color_target"] = ((ct[0]+rt)/2, (ct[1]+gt)/2, (ct[2]+bt)/2)
                    # If very close to opponent color, switch team
                    if color_distance(new_cell["color_target"], TEAM_COLORS[opp_team]) < 20:
                        new_cell["team"] = opp_team

            new_grid[y][x] = new_cell

    if chaos_enabled:
        # Random toggling
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if random.random() < RANDOM_TOGGLE_RATE:
                    c = new_grid[y][x]
                    if c["alive"]:
                        # kill cell
                        c["alive"] = False
                        c["team"] = None
                        c["color_target"] = BACKGROUND_COLOR
                        c["state_factor_target"] = 0.0
                    else:
                        # spawn cell
                        team = random.choice(["Blue", "Green"])
                        c["alive"] = True
                        c["team"] = team
                        c["color_target"] = TEAM_COLORS[team]
                        c["state_factor_target"] = 1.0

        # Color drift
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                c = new_grid[y][x]
                if c["alive"] and c["team"] is not None:
                    if random.random() < COLOR_DRIFT_CHANCE:
                        opp_team = "Blue" if c["team"] == "Green" else "Green"
                        rt, gt, bt = TEAM_COLORS[opp_team]
                        ct = c["color_target"]
                        c["color_target"] = ((ct[0]+rt)/2, (ct[1]+gt)/2, (ct[2]+bt)/2)
                        if color_distance(c["color_target"], TEAM_COLORS[opp_team]) < 40:
                            c["team"] = opp_team

    return new_grid

def interpolate_values(cell):
    sc = cell["state_factor_current"]
    st = cell["state_factor_target"]
    if abs(sc - st) > FADE_SPEED:
        sc += FADE_SPEED if sc < st else -FADE_SPEED
    else:
        sc = st
    cell["state_factor_current"] = sc

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
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            interpolate_values(grid[y][x])

def draw_grid(surface, grid):
    surface.fill(BACKGROUND_COLOR)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            factor = cell["state_factor_current"]
            if factor > 0:
                color = (int(cell["color_current"][0]),
                         int(cell["color_current"][1]),
                         int(cell["color_current"][2]))
                size = int((GRID_SIZE // 2) * factor + (GRID_SIZE // 2))
                cx = x * GRID_SIZE + GRID_SIZE // 2
                cy = y * GRID_SIZE + GRID_SIZE // 2
                pygame.draw.circle(surface, color, (cx, cy), size)

def calculate_scores(grid):
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
    pygame.display.set_caption("Chaotic Particle Battle with Delays")
    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

    running = True
    frame_count = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
               event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        time_elapsed = frame_count / FPS

        # Determine if we should run chaos
        chaos_enabled = (time_elapsed > START_DELAY_SECONDS) and (time_elapsed < CALM_DOWN_TIME_SECONDS)

        # Update the simulation only after the start delay
        if time_elapsed > START_DELAY_SECONDS:
            # Evolve
            grid = next_generation(grid, chaos_enabled)

        update_visuals(grid)
        draw_grid(render_surface, grid)
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        scores = calculate_scores(grid)
        render_text_with_border(screen, f"Blue: {scores['Blue']}", font, TEAM_COLORS["Blue"], 10, 10)
        render_text_with_border(screen, f"Green: {scores['Green']}", font, TEAM_COLORS["Green"], 10, 40)

        pygame.display.flip()
        clock.tick(FPS)
        frame_count += 1

    pygame.quit()

if __name__ == "__main__":
    main()
