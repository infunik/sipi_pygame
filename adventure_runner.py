import pygame
import random
import sqlite3
import sys
from pygame.locals import *

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)

# Player class
class Player:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.size = 20  # Store current size as a property
        self.rect = pygame.Rect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, self.size, self.size)
        self.speed = 5
        
    def update(self, keys):
        # 4-directional movement (top-down)
        if keys[K_a] or keys[K_LEFT]:
            self.rect.x -= self.speed
        if keys[K_d] or keys[K_RIGHT]:
            self.rect.x += self.speed
        if keys[K_w] or keys[K_UP]:
            self.rect.y -= self.speed
        if keys[K_s] or keys[K_DOWN]:
            self.rect.y += self.speed
            
        # Keep player within screen bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            
    def draw(self, screen):
        pygame.draw.rect(screen, BLUE, self.rect)
        
    def grow(self, amount=2):
        # Store current center position
        center_x, center_y = self.rect.center
        
        # Increase size
        self.size += amount
        
        # Cap size at a reasonable maximum
        max_size = 60
        self.size = min(self.size, max_size)
        
        # Update rect with new size while maintaining center position
        self.rect.width = self.size
        self.rect.height = self.size
        self.rect.center = (center_x, center_y)

# Obstacle class
class Obstacle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)  # Centered rectangle
        
    def draw(self, screen):
        # Draw a triangle instead of a circle
        points = [
            (self.rect.centerx, self.rect.top),  # Top point
            (self.rect.left, self.rect.bottom),  # Bottom left
            (self.rect.right, self.rect.bottom)  # Bottom right
        ]
        pygame.draw.polygon(screen, RED, points)
        
    def collides_with(self, other_rect):
        return self.rect.colliderect(other_rect)

# Bonus (Coin) class
class Bonus:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)  # Center the rectangle
        self.radius = 10
        
    def draw(self, screen):
        pygame.draw.circle(screen, YELLOW, self.rect.center, self.radius)
        
    def collides_with(self, other_rect):
        return self.rect.colliderect(other_rect)

# Button class for menus
class Button:
    def __init__(self, x, y, width, height, text, color=(200, 200, 200), hover_color=(150, 150, 150)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        self.font = pygame.font.Font(None, 36)
        
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)  # Border
        
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
        
    def is_clicked(self, pos, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# Database manager for high scores
class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_database()
        
    def init_database(self):
        try:
            # Create database if it doesn't exist
            self.conn = sqlite3.connect('highscore.db')
            self.cursor = self.conn.cursor()
            
            # Create table if it doesn't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY,
                    score INTEGER
                )
            ''')
            
            # Insert a default high score of 0 if the table is empty
            self.cursor.execute('SELECT COUNT(*) FROM scores')
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute('INSERT INTO scores (score) VALUES (?)', (0,))
                
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            
    def get_high_score(self):
        try:
            self.cursor.execute('SELECT MAX(score) FROM scores')
            result = self.cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except (sqlite3.Error, TypeError) as e:
            print(f"Error getting high score: {e}")
            return 0
            
    def update_high_score(self, score):
        try:
            current_high = self.get_high_score()
            if score > current_high:
                self.cursor.execute('INSERT INTO scores (score) VALUES (?)', (score,))
                self.conn.commit()
                return True
            return False
        except sqlite3.Error as e:
            print(f"Error updating high score: {e}")
            return False
            
    def close(self):
        if self.conn:
            self.conn.close()

# Main Game class
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Adventure Runner")
        self.clock = pygame.time.Clock()
        self.db_manager = DatabaseManager()
        
        # Game states
        self.MAIN_MENU = 0
        self.PLAYING = 1
        self.GAME_OVER = 2
        self.state = self.MAIN_MENU
        
        # Game objects
        self.player = Player()
        self.obstacles = []
        self.bonuses = []
        
        # Timers for spawning
        self.obstacle_timer = 0
        self.bonus_timer = 0
        
        # Difficulty system
        self.difficulty = 1
        self.max_difficulty = 10
        self.difficulty_timer = 0
        self.difficulty_interval = 30 * 60  # 30 seconds at 60 FPS
        self.game_time = 0  # Track total game time
        
        # Score
        self.score = 0
        self.high_score = self.db_manager.get_high_score()
        
        # Fonts
        self.font_small = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 48)
        
        # Buttons for menus
        self.main_menu_buttons = [
            Button(300, 250, 200, 50, "Start Game"),  # Changed from Russian to English
            Button(300, 350, 200, 50, "Exit")         # Changed from Russian to English
        ]
        
        self.game_over_buttons = [
            Button(300, 350, 200, 50, "Restart")    # Changed from Russian to English
        ]
        
        # Create game over overlay once
        self.game_over_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.game_over_overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                self.quit_game()
                
            mouse_pos = pygame.mouse.get_pos()
                
            if self.state == self.MAIN_MENU:
                for button in self.main_menu_buttons:
                    button.check_hover(mouse_pos)
                    if event.type == MOUSEBUTTONDOWN and button.is_clicked(mouse_pos, event):
                        if button.text == "Start Game":  # Start Game
                            self.start_game()
                        elif button.text == "Exit":  # Exit
                            self.quit_game()
                            
            elif self.state == self.GAME_OVER:
                for button in self.game_over_buttons:
                    button.check_hover(mouse_pos)
                    if event.type == MOUSEBUTTONDOWN and button.is_clicked(mouse_pos, event):
                        if button.text == "Restart":  # Restart
                            self.start_game()
                
    def start_game(self):
        self.state = self.PLAYING
        self.player.reset()
        self.obstacles = []
        self.bonuses = []
        self.score = 0
        self.obstacle_timer = 0
        self.bonus_timer = 0
        self.difficulty = 1
        self.difficulty_timer = 0
        self.game_time = 0
        
    def update(self):
        if self.state == self.PLAYING:
            # Update game time and difficulty
            self.game_time += 1
            self.difficulty_timer += 1
            
            # Increase difficulty level every 30 seconds
            if self.difficulty_timer >= self.difficulty_interval:
                if self.difficulty < self.max_difficulty:
                    self.difficulty += 1
                self.difficulty_timer = 0
            
            # Update player
            keys = pygame.key.get_pressed()
            self.player.update(keys)
            
            # Calculate disappearance chance based on difficulty
            disappear_chance = 0.005 + (self.difficulty * 0.005)  # 0.5% to 5.5%
            
            # Randomly remove obstacles and spawn new ones in their place
            for i in range(len(self.obstacles) - 1, -1, -1):
                if random.random() < disappear_chance:
                    old_pos = (self.obstacles[i].rect.centerx, self.obstacles[i].rect.centery)
                    self.obstacles.pop(i)
                    # Create a new obstacle near but not exactly at the same position
                    new_x = old_pos[0] + random.randint(-50, 50)
                    new_y = old_pos[1] + random.randint(-50, 50)
                    
                    # Keep within screen bounds
                    new_x = max(30, min(SCREEN_WIDTH - 30, new_x))
                    new_y = max(30, min(SCREEN_HEIGHT - 30, new_y))
                    
                    self.obstacles.append(Obstacle(new_x, new_y))
            
            # Spawn obstacles (more frequently at higher difficulty)
            self.obstacle_timer += 1
            spawn_interval = max(60, 300 - (self.difficulty * 25))  # 300 to 60 frames
            if self.obstacle_timer >= random.randint(spawn_interval // 2, spawn_interval):
                self.spawn_obstacle()
                self.obstacle_timer = 0
                
            # Spawn bonuses
            self.bonus_timer += 1
            bonus_interval = max(60, 240 - (self.difficulty * 15))  # 240 to 90 frames
            if self.bonus_timer >= random.randint(bonus_interval // 2, bonus_interval):
                self.spawn_bonus()
                self.bonus_timer = 0
                
            # Check collisions
            self.check_collisions()

    def spawn_obstacle(self):
        # Limit the number of obstacles to 1-20
        if len(self.obstacles) >= 20:
            return
            
        # Find a valid spawn position
        valid_position = False
        attempts = 0
        
        while not valid_position and attempts < 20:
            x = random.randint(30, SCREEN_WIDTH - 30)
            y = random.randint(30, SCREEN_HEIGHT - 30)
            new_obstacle = Obstacle(x, y)
            
            # Check if the position overlaps with existing obstacles
            overlap = False
            for obstacle in self.obstacles:
                if (abs(obstacle.rect.centerx - new_obstacle.rect.centerx) < 40 and 
                    abs(obstacle.rect.centery - new_obstacle.rect.centery) < 40):
                    overlap = True
                    break
                    
            # Check if the position is too close to the player
            if (abs(new_obstacle.rect.centerx - self.player.rect.centerx) < 100 and 
                abs(new_obstacle.rect.centery - self.player.rect.centery) < 100):
                overlap = True
                
            valid_position = not overlap
            attempts += 1
            
        if valid_position:
            self.obstacles.append(new_obstacle)

    def spawn_bonus(self):
        # Limit the number of bonuses to 10-20
        if len(self.bonuses) >= 20:
            return
            
        # Find a valid spawn position
        valid_position = False
        attempts = 0
        
        while not valid_position and attempts < 20:
            x = random.randint(30, SCREEN_WIDTH - 30)
            y = random.randint(30, SCREEN_HEIGHT - 30)
            new_bonus = Bonus(x, y)
            
            # Check if the position overlaps with existing bonuses
            overlap = False
            for bonus in self.bonuses:
                if (abs(bonus.rect.centerx - new_bonus.rect.centerx) < 30 and 
                    abs(bonus.rect.centery - new_bonus.rect.centery) < 30):
                    overlap = True
                    break
                    
            # Check if the position overlaps with obstacles
            for obstacle in self.obstacles:
                if (abs(obstacle.rect.centerx - new_bonus.rect.centerx) < 30 and 
                    abs(obstacle.rect.centery - new_bonus.rect.centery) < 30):
                    overlap = True
                    break
                    
            valid_position = not overlap
            attempts += 1
            
        if valid_position:
            self.bonuses.append(new_bonus)
    
    def check_collisions(self):
        # Check if player collides with obstacles
        for obstacle in self.obstacles[:]:
            if obstacle.collides_with(self.player.rect):
                self.game_over()
                
        # Check if player collides with bonuses
        for bonus in self.bonuses[:]:
            if bonus.collides_with(self.player.rect):
                self.bonuses.remove(bonus)
                self.score += 10
                self.player.grow()  # Make player bigger when collecting a coin
    
    def game_over(self):
        self.state = self.GAME_OVER
        # Update high score if needed
        if self.score > self.high_score:
            self.db_manager.update_high_score(self.score)
            self.high_score = self.score
    
    def draw(self):
        self.screen.fill(WHITE)
        
        if self.state == self.MAIN_MENU:
            # Draw title
            title_text = self.font_large.render("Adventure Runner", True, BLACK)
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 150))
            self.screen.blit(title_text, title_rect)
            
            # Draw high score
            high_score_text = self.font_small.render(f"High Score: {self.high_score}", True, BLACK)
            high_score_rect = high_score_text.get_rect(center=(SCREEN_WIDTH//2, 200))
            self.screen.blit(high_score_text, high_score_rect)
            
            # Draw menu buttons
            for button in self.main_menu_buttons:
                button.draw(self.screen)
                
        elif self.state == self.PLAYING or self.state == self.GAME_OVER:
            # Draw player
            self.player.draw(self.screen)
            
            # Draw obstacles
            for obstacle in self.obstacles:
                obstacle.draw(self.screen)
                
            # Draw bonuses
            for bonus in self.bonuses:
                bonus.draw(self.screen)
                
            # Draw UI panel with game info
            self.draw_game_ui()
            
            # If game over, show game over screen
            if self.state == self.GAME_OVER:
                self.draw_game_over_screen()
        
        pygame.display.flip()
    
    def draw_game_ui(self):
        # Draw score
        score_text = self.font_small.render(f"Score: {self.score}", True, BLACK)
        self.screen.blit(score_text, (10, 10))
        
        # Draw difficulty level
        difficulty_text = self.font_small.render(f"Level: {self.difficulty}/{self.max_difficulty}", True, BLACK)
        self.screen.blit(difficulty_text, (10, 40))
        
        # Draw countdown to next difficulty
        seconds_left = (self.difficulty_interval - self.difficulty_timer) // 60
        next_level_text = self.font_small.render(f"Next level: {seconds_left}s", True, BLACK)
        self.screen.blit(next_level_text, (10, 70))
        
        # Draw obstacle count
        obstacles_text = self.font_small.render(f"Obstacles: {len(self.obstacles)}/20", True, BLACK)
        self.screen.blit(obstacles_text, (10, 100))
        
        # Draw bonus count
        bonuses_text = self.font_small.render(f"Bonuses: {len(self.bonuses)}/20", True, BLACK)
        self.screen.blit(bonuses_text, (10, 130))
    
    def draw_game_over_screen(self):
        # Use pre-created overlay
        self.screen.blit(self.game_over_overlay, (0, 0))
        
        # Game over text
        game_over_text = self.font_large.render("Game Over", True, WHITE)  # Changed to English
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, 200))
        self.screen.blit(game_over_text, game_over_rect)
        
        # Final score
        final_score_text = self.font_small.render(f"Final Score: {self.score}", True, WHITE)  # Changed to English
        final_score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH//2, 250))
        self.screen.blit(final_score_text, final_score_rect)
        
        # High score
        high_score_text = self.font_small.render(f"High Score: {self.high_score}", True, WHITE)  # Changed to English
        high_score_rect = high_score_text.get_rect(center=(SCREEN_WIDTH//2, 280))
        self.screen.blit(high_score_text, high_score_rect)
        
        # Draw restart button
        for button in self.game_over_buttons:
            button.draw(self.screen)
    
    def quit_game(self):
        try:
            self.db_manager.close()
        except Exception as e:
            print(f"Error closing database: {e}")
        pygame.quit()
        sys.exit()
    
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()