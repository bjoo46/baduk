# 바둑 기보 (Baduk)

19×19 바둑판 진행 이미지 시리즈. 흑은 Claude가, 백은 사용자가 둡니다.

## 기보

| 파일 | 수순 | 설명 |
| --- | --- | --- |
| `go_board_1.png` | 흑 D16 | 흑 첫수. 좌상귀 4-4 화점 |
| `go_board_2.png` | 백 Q4 | 백이 대각 화점으로 응수 |
| `go_board_3.png` | 흑 Q16 | 흑이 우상귀 화점을 차지, 상변 구도 |
| `go_board_4.png` | 백 D4 | 백이 좌하귀 화점, 하변 구도 |
| `go_board_5.png` | 흑 K16 | 흑이 상변 화점으로 D16–Q16 사이 확장 |
| `go_board_6.png` | 백 K4 | 백이 하변 화점, 상하 대칭 구도 |
| `go_board_7.png` | 흑 K10 | 흑이 천원을 차지, 대칭을 깨고 중앙 선점 |

## 좌표 표기

19×19 표준 좌표계. 가로는 `A`–`T` (`I` 제외), 세로는 `1`–`19` (아래가 1).

- **D16 / Q16** — 좌상귀·우상귀 4-4 화점
- **D4 / Q4** — 좌하귀·우하귀 4-4 화점
- **K16 / K10 / K4** — 상변·천원·하변 화점

`I`를 건너뛰는 것은 세로선 1과 숫자 1의 혼동을 피하기 위한 관례입니다.

## 국면

![흑 D16 → 백 Q4 → 흑 Q16 → 백 D4 → 흑 K16 → 백 K4 → 흑 K10](go_board_7.png)

## 도구

`baduk_tools.py` — 바둑판 이미지에서 국면을 읽고 돌을 덮어 그립니다.

```
python baduk_tools.py read <image>
python baduk_tools.py play <src> <dst> <gx> <gy>
```

`gx`는 좌→우 0–18, `gy`는 위→아래 0–18. 예: D16 = `3 3`, K16 = `9 3`, K10 = `9 9`.

## 자동화

`go_board_*.png` 가 push되면 두 워크플로가 각자 자기 차례인지 확인하고, 차례일 때만 한 수를 둡니다.

- `.github/workflows/black-move.yml` — 흑. `.github/black-move.md` 지시로 Claude가 착수
- `.github/workflows/white-reply.yml` — 백. `auto_white.py` 로 합법수를 검증하고 Codex가 선정
