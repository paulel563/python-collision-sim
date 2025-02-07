import pygame
import random
import math

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

# Game of Life rules:
BIRTH_RULE = [3]           # Birth with 3 neighbors
SURVIVAL_RULE = [2, 3, 4]  # Survive with 2-4 neighbors

NUM_STARTING_PARTICLES = 200  # total

TEAM_COLORS = {
    "Blue": (0, 100, 255),
    "Green": (0, 200, 0)
}
BACKGROUND_COLOR = (10, 10, 30)

FADE_SPEED = 0.25         # Speed of fade in/out
COLOR_BLEND_SPEED = 0.37  # Speed of color transitions

CONVERSION_THRESHOLD = 4  # Aggressiveness for color conversions

# Chaos probabilities:
# During the main battle, we'll start with these base rates.
INITIAL_TOGGLE_RATE = 0.009
INITIAL_DRIFT_CHANCE = 0.05

SEED = 69
SCORE_FONT_SIZE = 24
pygame.init()
pygame.font.init()
font = pygame.font.SysFont("Arial", SCORE_FONT_SIZE)

# ----------------------------
# Timing Flow
# ----------------------------
START_DELAY_SECONDS = 2       # no updates, just show initial
BATTLE_PHASE_SECONDS = 8      # total chaos with toggles/drifts
CALM_DOWN_DURATION = 4        # we linearly ramp chaos down to zero over these 4 seconds
# After that, we do no more births/deaths nor chaos, just interpolation

# Derived times
BATTLE_END = START_DELAY_SECONDS + BATTLE_PHASE_SECONDS
CALM_END   = BATTLE_END + CALM_DOWN_DURATION


def initialize_seed(seed):
    random.seed(seed)


def create_grid(num_particles):
    """
    Create an empty grid, then place exactly num_particles cells
    in small random clusters of size 2-4. Half Blue, half Green.
    """
    grid = []
    for _ in range(GRID_HEIGHT):
        row = []
        for _ in range(GRID_WIDTH):
            cell = {
                "alive": False,
                "team": None,
                "color_current": BACKGROUND_COLOR,
                "color_target": BACKGROUND_COLOR,
                "state_factor_current": 0.0,
                "state_factor_target": 0.0
            }
            row.append(cell)
        grid.append(row)

    blue_count = num_particles // 2
    green_count = num_particles - blue_count

    def expand_cluster(positions):
        """Pick an empty neighbor around the cluster to expand."""
        candidates = []
        for (px, py) in positions:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if not grid[ny][nx]["alive"]:
                            candidates.append((nx, ny))
        random.shuffle(candidates)
        for (cx, cy) in candidates:
            if (cx, cy) not in positions:
                positions.append((cx, cy))
                return positions
        return positions

    def set_cell_alive(x, y, team):
        grid[y][x]["alive"] = True
        grid[y][x]["team"] = team
        grid[y][x]["color_current"] = TEAM_COLORS[team]
        grid[y][x]["color_target"] = TEAM_COLORS[team]
        grid[y][x]["state_factor_current"] = 1.0
        grid[y][x]["state_factor_target"] = 1.0

    def place_cluster(team, cluster_size):
        attempts = 0
        placed_positions = []
        while attempts < 100:
            attempts += 1
            sx = random.randint(0, GRID_WIDTH - 1)
            sy = random.randint(0, GRID_HEIGHT - 1)
            if not grid[sy][sx]["alive"]:
                placed_positions = [(sx, sy)]
                for _ in range(cluster_size - 1):
                    placed_positions = expand_cluster(placed_positions)
                if len(placed_positions) == cluster_size:
                    break
                else:
                    placed_positions = []

        for (x, y) in placed_positions:
            set_cell_alive(x, y, team)
        return len(placed_positions)

    # Place Blue clusters
    to_place_blue = blue_count
    while to_place_blue > 0:
        csize = random.randint(2, 4)
        csize = min(csize, to_place_blue)
        placed = place_cluster("Blue", csize)
        to_place_blue -= placed

    # Place Green clusters
    to_place_green = green_count
    while to_place_green > 0:
        csize = random.randint(2, 4)
        csize = min(csize, to_place_green)
        placed = place_cluster("Green", csize)
        to_place_green -= placed

    return grid


NEIGHBOR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),            (1, 0),
    (-1, 1),  (0, 1),  (1, 1)
]


def count_neighbors(grid, x, y):
    alive_count = 0
    team_counts = {"Blue": 0, "Green": 0}
    for dx, dy in NEIGHBOR_OFFSETS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
            neigh = grid[ny][nx]
            if neigh["alive"]:
                alive_count += 1
                if neigh["team"]:
                    team_counts[neigh["team"]] += 1
    return alive_count, team_counts


def is_border_cell(grid, x, y):
    """A cell is a border if it has at least one neighbor of the opposite team."""
    if not grid[y][x]["alive"]:
        return False
    my_team = grid[y][x]["team"]
    if my_team is None:
        return False
    opp_team = "Blue" if my_team == "Green" else "Green"
    for dx, dy in NEIGHBOR_OFFSETS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
            neigh = grid[ny][nx]
            if neigh["alive"] and neigh["team"] == opp_team:
                return True
    return False


def color_distance(c1, c2):
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])


def determine_team_on_birth(team_counts):
    blue_n = team_counts["Blue"]
    green_n = team_counts["Green"]
    if blue_n > green_n:
        return "Blue"
    elif green_n > blue_n:
        return "Green"
    else:
        return random.choice(["Blue", "Green"])


def game_of_life_step(grid):
    """
    Standard GoL update + conversion threshold (no toggles/drifts).
    """
    new_grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            cell = grid[y][x]
            alive_count, team_counts = count_neighbors(grid, x, y)

            was_alive = cell["alive"]
            my_team = cell["team"]

            # Game of Life birth/survival
            if was_alive:
                will_live = (alive_count in SURVIVAL_RULE)
            else:
                will_live = (alive_count in BIRTH_RULE)

            if will_live:
                # Keep same team if still alive, else new birth
                team = my_team if was_alive else determine_team_on_birth(team_counts)
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

            # Conversion threshold
            if will_live and team:
                opp_team = "Blue" if team == "Green" else "Green"
                own_count = team_counts[team]
                opp_count = team_counts[opp_team]
                if opp_count >= own_count * CONVERSION_THRESHOLD and opp_count > 0:
                    rt, gt, bt = TEAM_COLORS[opp_team]
                    ct = new_cell["color_target"]
                    new_cell["color_target"] = (
                        (ct[0] + rt) / 2,
                        (ct[1] + gt) / 2,
                        (ct[2] + bt) / 2
                    )
                    if color_distance(new_cell["color_target"], TEAM_COLORS[opp_team]) < 20:
                        new_cell["team"] = opp_team

            new_grid[y][x] = new_cell

    return new_grid


def apply_chaos(grid, toggle_rate, drift_rate):
    """
    Border toggles + border drifts, with specified rates.
    """
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            c = grid[y][x]
            if c["alive"] and c["team"] is not None and is_border_cell(grid, x, y):
                # Instant team flip
                if random.random() < toggle_rate:
                    opp_team = "Blue" if c["team"] == "Green" else "Green"
                    c["team"] = opp_team
                    c["color_target"] = TEAM_COLORS[opp_team]
                # Color drift
                if random.random() < drift_rate:
                    opp_team = "Blue" if c["team"] == "Green" else "Green"
                    rt, gt, bt = TEAM_COLORS[opp_team]
                    ct = c["color_target"]
                    c["color_target"] = (
                        (ct[0] + rt) / 2,
                        (ct[1] + gt) / 2,
                        (ct[2] + bt) / 2
                    )
                    if color_distance(c["color_target"], TEAM_COLORS[opp_team]) < 40:
                        c["team"] = opp_team


def interpolate_values(cell):
    # Fade factor
    sc = cell["state_factor_current"]
    st = cell["state_factor_target"]
    if abs(sc - st) > FADE_SPEED:
        sc += FADE_SPEED if sc < st else -FADE_SPEED
    else:
        sc = st
    cell["state_factor_current"] = sc

    # Color
    cc = cell["color_current"]
    ct = cell["color_target"]
    r_new = cc[0] + (ct[0] - cc[0]) * COLOR_BLEND_SPEED
    g_new = cc[1] + (ct[1] - cc[1]) * COLOR_BLEND_SPEED
    b_new = cc[2] + (ct[2] - cc[2]) * COLOR_BLEND_SPEED
    cell["color_current"] = (r_new, g_new, b_new)


def update_visuals(grid):
    for row in grid:
        for cell in row:
            interpolate_values(cell)


def draw_grid(surface, grid):
    surface.fill(BACKGROUND_COLOR)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            c = grid[y][x]
            factor = c["state_factor_current"]
            if factor > 0:
                color = (
                    int(c["color_current"][0]),
                    int(c["color_current"][1]),
                    int(c["color_current"][2])
                )
                size = int((GRID_SIZE // 2) * factor + (GRID_SIZE // 2))
                cx = x * GRID_SIZE + GRID_SIZE // 2
                cy = y * GRID_SIZE + GRID_SIZE // 2
                pygame.draw.circle(surface, color, (cx, cy), size)


def calculate_scores(grid):
    scores = {"Blue": 0, "Green": 0}
    for row in grid:
        for cell in row:
            if cell["alive"] and cell["team"]:
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


def is_grid_stable(grid, color_epsilon=1.0, factor_epsilon=0.01):
    """Check if all cells are done transitioning color and factor."""
    for row in grid:
        for c in row:
            sc = c["state_factor_current"]
            st = c["state_factor_target"]
            if abs(sc - st) > factor_epsilon:
                return False
            cc, ct = c["color_current"], c["color_target"]
            if (abs(cc[0] - ct[0]) > color_epsilon or
                abs(cc[1] - ct[1]) > color_epsilon or
                abs(cc[2] - ct[2]) > color_epsilon):
                return False
    return True


def main():
    initialize_seed(SEED)
    grid = create_grid(NUM_STARTING_PARTICLES)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Smooth Calm Particle Battle")
    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
    clock = pygame.time.Clock()

    running = True
    frame_count = 0

    final_scores = None
    stable_after_freeze = False

    while running:
        dt = clock.tick(FPS) / 1000.0
        time_elapsed = frame_count / FPS

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
               event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # PHASE 0: Show initial layout (no changes)
        if time_elapsed < START_DELAY_SECONDS:
            pass  # do nothing

        # PHASE 1: Full chaos (GoL + toggles/drifts)
        elif time_elapsed < BATTLE_END:
            # Game of Life
            grid = game_of_life_step(grid)
            # Apply chaos with full rates
            apply_chaos(grid, INITIAL_TOGGLE_RATE, INITIAL_DRIFT_CHANCE)

        # PHASE 2: Ramping chaos down
        elif time_elapsed < CALM_END:
            # Time since the battle ended
            t_since_battle_end = time_elapsed - BATTLE_END
            ramp_progress = min(1.0, max(0.0, t_since_battle_end / CALM_DOWN_DURATION))
            # Interpolate chaos rates from initial -> 0
            toggle_rate = INITIAL_TOGGLE_RATE * (1.0 - ramp_progress)
            drift_rate  = INITIAL_DRIFT_CHANCE * (1.0 - ramp_progress)

            # Standard GoL
            grid = game_of_life_step(grid)
            # But chaos gets weaker each frame
            apply_chaos(grid, toggle_rate, drift_rate)

        # PHASE 3: Freeze logic, let visuals finish
        else:
            if not stable_after_freeze:
                # Check if everything's stable
                if is_grid_stable(grid):
                    final_scores = calculate_scores(grid)
                    stable_after_freeze = True
            # No births/deaths or toggles/drifts

        # Always do interpolation
        update_visuals(grid)

        # Draw
        draw_grid(render_surface, grid)
        scaled_surface = pygame.transform.smoothscale(render_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Score Display
        if final_scores:
            # Final scoreboard locked in
            render_text_with_border(screen, f"Blue: {final_scores['Blue']}", font, TEAM_COLORS["Blue"], 10, 10)
            render_text_with_border(screen, f"Green: {final_scores['Green']}", font, TEAM_COLORS["Green"], 10, 40)
        else:
            # Show live scoreboard
            current_scores = calculate_scores(grid)
            render_text_with_border(screen, f"Blue: {current_scores['Blue']}", font, TEAM_COLORS["Blue"], 10, 10)
            render_text_with_border(screen, f"Green: {current_scores['Green']}", font, TEAM_COLORS["Green"], 10, 40)

        pygame.display.flip()
        frame_count += 1

    pygame.quit()


if __name__ == "__main__":
    main()
