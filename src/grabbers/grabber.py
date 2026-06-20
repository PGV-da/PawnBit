from abc import ABC, abstractmethod

from utilities import attach_to_session


# Base abstract class for different chess sites
class Grabber(ABC):
    def __init__(self, chrome_url, chrome_session_id):
        self.chrome = attach_to_session(chrome_url, chrome_session_id)
        self._board_elem = None
        self.moves_list = {}

    def get_board(self):
        return self._board_elem

    # Resets the moves list when changing games
    def reset_moves_list(self):
        """Reset the moves list when a new game starts"""
        self.moves_list = {}

    # Returns the coordinates of the top left corner of the ChromeDriver viewport on screen.
    # DEPRECATED – use get_board_screen_rect() for accurate absolute screen coordinates.
    def get_top_left_corner(self):
        canvas_x_offset = self.chrome.execute_script("return window.screenLeft - window.scrollX;")
        canvas_y_offset = self.chrome.execute_script("return window.screenTop - window.scrollY;")
        return canvas_x_offset, canvas_y_offset

    def get_board_screen_rect(self):
        """
        Returns the chess board element's absolute position on screen as
        {x, y, width, height} using a single JavaScript getBoundingClientRect()
        call.  This is the only reliable way to get the exact screen coordinates
        because getBoundingClientRect() gives the viewport-relative rect, and
        window.screenLeft/screenTop give the screen position of the viewport –
        no multi-step offset arithmetic that can drift.
        """
        board = self._board_elem
        if board is None:
            return None
        return self.chrome.execute_script("""
            var rect = arguments[0].getBoundingClientRect();
            return {
                x: Math.round(rect.left + window.screenLeft),
                y: Math.round(rect.top  + window.screenTop),
                width:  Math.round(rect.width),
                height: Math.round(rect.height)
            };
        """, board)

    # Sets the _board_elem variable
    @abstractmethod
    def update_board_elem(self):
        pass

    # Returns True if white, False if black,
    # None if the color is not found
    @abstractmethod
    def is_white(self):
        pass

    # Checks if the game over window popup is open
    # Returns True if it is, False if it isn't
    @abstractmethod
    def is_game_over(self):
        pass

    # Returns the current board move list
    # Ex. ["e4", "c5", "Nf3"]
    @abstractmethod
    def get_move_list(self):
        pass

    # Returns True if the player does puzzles
    # and False if not
    @abstractmethod
    def is_game_puzzles(self):
        pass

    # Clicks the next button on the puzzles page
    @abstractmethod
    def click_puzzle_next(self):
        pass

    # Makes a mouseless move
    @abstractmethod
    def make_mouseless_move(self, move, move_count):
        pass
