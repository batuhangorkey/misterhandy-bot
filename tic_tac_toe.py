class Table:
    def __init__(self):
        self.player1 = b'000000000'
        self.player2 = b'000000000'
        self.mask = int(self.player1) | int(self.player2)


class Board:
    def __init__(self):
        self.current_table = Table()

    def view_table(self):
        string_table = []
        for i in range(9):
            if self.current_table.player1[i] == 49:
                string_table += 'x'
            elif self.current_table.player2[i] == 49:
                string_table += 'o'
            else:
                string_table += '+'
        for i in range(0, 9, 3):
            print(' '.join(string_table[i:i + 3]))
        print()

    def win_check(self):
        if self.current_table.player1.find(b'111') > -1:
            print('X won.')
            return 2
        if self.current_table.player2.find(b'111') > -1:
            print('O won.')
            return 1
        if self.current_table.mask == b'111111111':
            print('Draw.')
            return 0
        return -1

    def play_at_location(self, location):
        self.current_table.player1 = bytes(int(self.current_table.player1) | 1 << location)

    @classmethod
    def validate(cls, _input: str):
        coordinate = [int(_) for _ in _input.split()]
        return coordinate[0] + ((coordinate[1] - 1) * 3) - 1


board = Board()
while board.win_check() == -1:
    board.view_table()
    board.play_at_location(board.validate(input()))
    board.view_table()
