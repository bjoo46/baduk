import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from baduk_tools import read, draw
from auto_white import restore_intersection
from go_rules import play, transition
from PIL import Image

ROOT = Path(__file__).resolve().parent

class RulesTests(unittest.TestCase):
    def test_both_colors_capture_and_transition(self):
        for color, enemy in [('B', 'W'), ('W', 'B')]:
            before = {(1,1):enemy, (0,1):color, (1,0):color, (2,1):color}
            after, captured = play(before, (1,2), color)
            self.assertEqual(captured, {(1,1)})
            self.assertEqual(transition(before, after, color), ((1,2), captured))

    def test_capture_multiple_stone_group(self):
        before = {(1,1):'B', (2,1):'B', (0,1):'W', (1,0):'W',
                  (2,0):'W', (3,1):'W', (2,2):'W'}
        self.assertEqual(play(before, (1,2), 'W')[1], {(1,1),(2,1)})

    def test_suicide_occupied_bounds_and_repeat(self):
        board = {(0,1):'B',(1,0):'B',(2,1):'B',(1,2):'B'}
        for point in [(1,1),(0,1),(-1,0),(19,0)]:
            with self.assertRaises(ValueError):
                play(board, point, 'W')
        after, _ = play({}, (4,4), 'B')
        with self.assertRaisesRegex(ValueError, 'ko'):
            play({}, (4,4), 'B', [after])

    def test_capture_before_suicide_and_immediate_ko(self):
        # White capture fills its only empty neighbor; removed Black supplies liberty.
        before = {(1,1):'B', (0,1):'W', (1,0):'W', (2,1):'W',
                  (0,2):'B', (2,2):'B', (1,3):'B'}
        after, captured = play(before, (1,2), 'W')
        self.assertEqual(captured, {(1,1)})
        with self.assertRaisesRegex(ValueError, 'ko'):
            play(after, (1,1), 'B', [before])

    def test_real_first_capture_and_turn_after_capture(self):
        before = read(ROOT/'go_board_21.png')[0]
        after = read(ROOT/'go_board_22.png')[0]
        self.assertEqual(transition(before, after, 'W'), ((1,4), {(2,4)}))
        with tempfile.TemporaryDirectory() as temp:
            for n in range(1,23):
                (Path(temp)/f'go_board_{n}.png').write_bytes((ROOT/f'go_board_{n}.png').read_bytes())
            result = subprocess.check_output([sys.executable, '-B', str(ROOT/'baduk_tools.py'), 'turn'],
                                             cwd=temp, text=True)
            self.assertIn('turn=black', result)

    def test_capture_rendering_and_restore_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'capture.png'
            subprocess.check_call([sys.executable,'-B',str(ROOT/'baduk_tools.py'),'play',
                                   str(ROOT/'go_board_21.png'),str(target),'1','4','W'],cwd=temp)
            self.assertEqual(read(target)[0], read(ROOT/'go_board_22.png')[0])
        pos, xs, ys, spacing = read(ROOT/'go_board_1.png')
        for point in [(0,0),(18,18),(0,9),(9,18),(3,3),(5,5)]:
            img = Image.open(ROOT/'go_board_1.png').convert('RGB')
            draw(img,xs,ys,spacing,*point,'W')
            restore_intersection(img,xs,ys,spacing,point)
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'restored.png'
                img.save(path)
                expected=dict(pos)
                expected.pop(point,None)
                self.assertEqual(read(path)[0],expected)

if __name__ == '__main__':
    unittest.main()
