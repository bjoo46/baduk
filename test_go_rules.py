import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from baduk_tools import read, draw, _complete_grid_axis, save_move
from annotate_move import annotate, STRIP
from auto_white import restore_intersection
from go_rules import play, transition
from PIL import Image

ROOT = Path(__file__).resolve().parent

class RulesTests(unittest.TestCase):
    def test_footer_does_not_affect_detection_or_accumulate(self):
        source=ROOT/'go_board_22.png'
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'go_board_22.png'
            img=Image.open(source).convert('RGB')
            save_move(img,path,1,4,'W')
            self.assertEqual(read(path)[0],read(source)[0])
            with Image.open(path) as first:
                size=first.size
                self.assertEqual(size,(img.width,img.height+STRIP))
                self.assertEqual(first.info['baduk_last_move'],'22 W B15')
                self.assertEqual(first.crop((0,0,img.width,img.height)).tobytes(),img.tobytes())
            annotate(path,22,'W','B15')
            with Image.open(path) as second:
                self.assertEqual(second.size,size)
            self.assertEqual(read(path)[0],read(source)[0])

    def test_hidden_internal_grid_line(self):
        axis = [61.5+40*i for i in range(19)]
        self.assertEqual(_complete_grid_axis(axis[:3]+axis[4:]), axis)
        # Missing outer boundaries cannot be inferred safely.
        self.assertEqual(_complete_grid_axis(axis[1:]), axis[1:])

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
