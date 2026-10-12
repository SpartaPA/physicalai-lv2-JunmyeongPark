# lv2_module3

모듈3 추가과제 — HSV Mask·검출 설정값 비교 실험 (박준명, [JunmyeongPark](https://github.com/JunmyeongPark))

| 문서 | 내용 |
|---|---|
| [`report.md`](report.md) | 보고서: 실행 환경, 입력 bag(출처·구간), 실험 1(HSV 범위 A/B), 실험 2(min_area A/B), no-target 확인, 결론·한계 |
| [`hsv_ws/README.md`](hsv_ws/README.md) | 빌드·실행·튜닝·기록·집계 명령 (재현 방법) |
| [`results/`](results/) | 실험별 비교 이미지 (`exp1/`, `exp2/`, `no_target/`) |

- 코드: [`hsv_ws/src/hsv_detector/`](hsv_ws/src/hsv_detector/) — 19강 `ColorDetector` + 21강 cv_bridge ROS 2 노드
- 환경: Ubuntu 24.04.5, ROS 2 Jazzy, Python 3.12.3, OpenCV 4.6.0
- 입력: 팀 프로젝트(2026-10-08) rosbag 재생 (실시간 카메라 아님). bag 파일은 용량 때문에 저장소에 넣지 않았고, 출처는 report.md 3절에 적었다.
