import json
import os
import random
import sys

import pygame

WIDTH, HEIGHT = 1000, 600
FPS = 120
BG = (20, 24, 38)
FG = (235, 235, 240)
ACCENT = (255, 200, 60)


def save_path():
    """File lưu điểm cao nằm cạnh file exe (hoặc cạnh pong.py khi chạy thường)."""
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
        else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "highscore.json")


def load_high_score():
    try:
        with open(save_path(), "r") as f:
            return json.load(f).get("high_score", 0)
    except (FileNotFoundError, ValueError):
        return 0


def save_high_score(score):
    try:
        with open(save_path(), "w") as f:
            json.dump({"high_score": score}, f)
    except OSError:
        pass  # không ghi được thì bỏ qua, không làm game bị lỗi


# ---------- Lớp cha: mọi vật thể trong game ----------
class Entity(pygame.sprite.Sprite):
    def __init__(self, size, pos, groups):
        super().__init__(groups)
        self.image = pygame.Surface(size)
        self.image.fill(FG)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(self.rect.center)


# ---------- Lớp con: thanh đỡ ----------
class Paddle(Entity):
    def __init__(self, pos, groups, speed=600):
        super().__init__((18, 110), pos, groups)
        self.speed = speed
        self.direction = 0

    def move(self, dt):
        self.pos.y += self.direction * self.speed * dt
        self.pos.y = max(self.rect.height / 2,
                         min(HEIGHT - self.rect.height / 2, self.pos.y))
        self.rect.centery = round(self.pos.y)


class Player(Paddle):
    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.direction = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) \
            - int(keys[pygame.K_w] or keys[pygame.K_UP])
        self.move(dt)


class Opponent(Paddle):
    def __init__(self, pos, groups, ball):
        super().__init__(pos, groups, speed=380)
        self.ball = ball

    def update(self, dt):
        # AI đi theo bóng, có độ trễ nhỏ để người chơi còn thắng được
        if abs(self.ball.rect.centery - self.rect.centery) > 12:
            self.direction = 1 if self.ball.rect.centery > self.rect.centery else -1
        else:
            self.direction = 0
        self.move(dt)


# ---------- Quả bóng ----------
class Ball(Entity):
    def __init__(self, groups, paddles, on_score):
        super().__init__((20, 20), (WIDTH / 2, HEIGHT / 2), groups)
        self.paddles = paddles
        self.on_score = on_score
        self.speed = 420
        self.direction = pygame.Vector2()
        self.reset()

    def reset(self):
        self.pos.update(WIDTH / 2, HEIGHT / 2)
        self.rect.center = self.pos
        self.speed = 420
        self.direction.update(random.choice((-1, 1)), random.uniform(-0.6, 0.6))
        self.direction = self.direction.normalize()

    def update(self, dt):
        # Di chuyển từng trục để xử lý va chạm chính xác
        self.pos.x += self.direction.x * self.speed * dt
        self.rect.centerx = round(self.pos.x)
        self.collide_paddles("horizontal")

        self.pos.y += self.direction.y * self.speed * dt
        self.rect.centery = round(self.pos.y)
        self.collide_paddles("vertical")

        # Chạm tường trên/dưới
        if self.rect.top <= 0:
            self.rect.top = 0
            self.pos.y = self.rect.centery
            self.direction.y *= -1
        elif self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.pos.y = self.rect.centery
            self.direction.y *= -1

        # Ra khỏi biên trái/phải thì ghi điểm
        if self.rect.right < 0:
            self.on_score("opponent")
            self.reset()
        elif self.rect.left > WIDTH:
            self.on_score("player")
            self.reset()

    def collide_paddles(self, axis):
        for paddle in self.paddles:
            if not self.rect.colliderect(paddle.rect):
                continue
            if axis == "horizontal":
                if self.direction.x > 0:
                    self.rect.right = paddle.rect.left
                else:
                    self.rect.left = paddle.rect.right
                self.pos.x = self.rect.centerx
                self.direction.x *= -1
                # Đánh lệch tâm thanh đỡ thì bóng đổi góc
                offset = (self.rect.centery - paddle.rect.centery) / (paddle.rect.height / 2)
                self.direction.y = max(-0.9, min(0.9, offset))
                self.direction = self.direction.normalize()
                self.speed = min(self.speed + 25, 900)
            else:
                if self.direction.y > 0:
                    self.rect.bottom = paddle.rect.top
                else:
                    self.rect.top = paddle.rect.bottom
                self.pos.y = self.rect.centery
                self.direction.y *= -1


# ---------- Game chính ----------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pong")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 90)
        self.small = pygame.font.Font(None, 32)

        self.all_sprites = pygame.sprite.Group()
        self.paddle_sprites = pygame.sprite.Group()

        self.player = Player((40, HEIGHT / 2), (self.all_sprites, self.paddle_sprites))
        self.ball = Ball(self.all_sprites, self.paddle_sprites, self.add_score)
        self.opponent = Opponent((WIDTH - 40, HEIGHT / 2),
                                 (self.all_sprites, self.paddle_sprites), self.ball)

        self.score = {"player": 0, "opponent": 0}
        self.high_score = load_high_score()
        self.running = True

    def add_score(self, who):
        self.score[who] += 1
        if self.score["player"] > self.high_score:
            self.high_score = self.score["player"]
            save_high_score(self.high_score)

    def draw_text(self, text, font, color, center):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=center))

    def draw(self):
        self.screen.fill(BG)
        for y in range(0, HEIGHT, 30):  # đường kẻ giữa sân
            pygame.draw.rect(self.screen, (60, 66, 90), (WIDTH // 2 - 2, y, 4, 16))
        self.all_sprites.draw(self.screen)

        self.draw_text(str(self.score["player"]), self.font, FG, (WIDTH / 2 - 80, 60))
        self.draw_text(str(self.score["opponent"]), self.font, FG, (WIDTH / 2 + 80, 60))
        self.draw_text(f"High score: {self.high_score}   |   W/S or Up/Down to move   |   ESC to quit",
                       self.small, ACCENT, (WIDTH / 2, HEIGHT - 24))
        pygame.display.update()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000  # delta time (giây)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or \
                        (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self.running = False

            self.all_sprites.update(dt)
            self.draw()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
