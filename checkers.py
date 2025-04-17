import pygame
from typing import Literal

WIDTH, HEIGHT = 600, 600
ROWS, COLS = 8, 8
SQUARE_SIZE = WIDTH // COLS

RED = (255, 0, 0)
WHITE = (204, 197, 190)
BLACK = (56, 51, 45)
GREY = (128, 128, 128)
PIECE_WHITE = (255, 255, 255)
PIECE_BLACK = (0, 0, 0)


class Checkers:
    def __init__(self, side: Literal["w", "b"]) -> None:
        pygame.init()

        self.side = side
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

        pygame.display.set_caption("Camel Checkers")

    def draw_board(self) -> None:
        self.screen.fill(WHITE if self.side == "b" else BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(self.screen, BLACK if self.side == "b" else WHITE,
                                 (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def draw_pieces(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                if (row + col) % 2 == 1:
                    center_x = col * SQUARE_SIZE + SQUARE_SIZE // 2
                    center_y = row * SQUARE_SIZE + SQUARE_SIZE // 2
                    radius = SQUARE_SIZE // 2 - 10

                    if row < 3:
                        color = PIECE_WHITE if self.side == "b" else PIECE_BLACK
                        pygame.draw.circle(self.screen, color, (center_x, center_y), radius)
                        pygame.draw.circle(self.screen, GREY, (center_x, center_y), radius, 2)

                    elif row > 4:
                        color = PIECE_BLACK if self.side == "b" else PIECE_WHITE
                        pygame.draw.circle(self.screen, color, (center_x, center_y), radius)
                        pygame.draw.circle(self.screen, GREY, (center_x, center_y), radius, 2)

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.draw_board()
            self.draw_pieces()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Checkers("w").run()
