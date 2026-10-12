# hsv_ws — HSV 색상 검출 노드 워크스페이스

19강 `ColorDetector`(블러 → HSV → inRange → 열림·닫힘 → 컨투어 → 면적·형상 필터 → 모멘트 중심 → EMA)를
21강 구조(cv_bridge 노드, 비전 로직과 배관 분리, header 계승)로 감싼 ROS 2 패키지 `hsv_detector`.
모터 제어 없음. 입력은 기록된 rosbag 재생.

```
hsv_ws/
├── bags/                      # 입력 bag (git 제외, 아래 "입력 준비")
├── out/                       # 실험 출력 bag (git 제외)
└── src/hsv_detector/
    ├── hsv_detector/
    │   ├── color_detector.py       # 19강 비전 모듈 (ROS 의존 없음)
    │   ├── color_detector_node.py  # 21강 노드: 구독·변환·발행
    │   └── bag_tools.py            # 출력 bag 집계(summary)·이미지 추출(export)
    ├── config/  base.yaml  exp1_A.yaml exp1_B.yaml  exp2_A.yaml exp2_B.yaml
    ├── launch/  detector.launch.py  # 단일 또는 A/B 동시 실행
    └── test/    test_color_detector.py
```

## 1. 빌드

```bash
sudo apt install ros-$ROS_DISTRO-cv-bridge python3-opencv   # 없으면
cd ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws
colcon build --symlink-install
source install/setup.bash
python3 -m pytest -q src/hsv_detector/test      # 순수 모듈 테스트
```

## 2. 입력 준비 (팀 프로젝트 bag 재사용)

```bash
mkdir -p ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/bags && cd ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/bags
Z=~/Downloads/bags-20261008T082834Z-1-001.zip
unzip -j $Z 'bags/RAW-01/*'   -d RAW-01
unzip -j $Z 'bags/BAG-OK/*'   -d BAG-OK
unzip -j $Z 'bags/BAG-LOST/*' -d BAG-LOST
sha256sum */*.mcap
```

| bag | 이미지 토픽 | 타입 |
|---|---|---|
| RAW-01 | `/camera/camera/color/image_raw` | sensor_msgs/Image (rgb8) → `input_compressed:=false` |
| BAG-OK, BAG-LOST | `/camera/color/jpeg` | sensor_msgs/CompressedImage → `input_compressed:=true` |

## 3. 노드 토픽

| 방향 | 토픽 (A/B 실행 시 `/A/…`, `/B/…`) | 타입 | 내용 |
|---|---|---|---|
| 구독 | `image_topic` 파라미터 | Image 또는 CompressedImage | 입력 프레임 |
| 발행 | `image_input` | Image bgr8 | 검출에 들어간 원본 프레임 (Raw Image 증빙) |
| 발행 | `mask` | Image mono8 | HSV Mask |
| 발행 | `image_annotated` | Image bgr8 | bbox·중심 오버레이 |
| 발행 | `detection` | PointStamped | 검출 시에만. x,y = 중심 px (EMA), z = 면적 px² |
| 발행 | `detection_stats` | String(JSON) | 매 프레임. detected, 컨투어 수, 필터 통과 수, mask 픽셀 수, 처리 시간 |

모든 출력 header = 입력 프레임 header. 시작 시 로그에 Python·OpenCV·ROS_DISTRO 버전이 찍힌다.

검출 파라미터 `h_lo h_hi s_lo s_hi v_lo v_hi min_area min_circularity ema_alpha blur_ksize morph_ksize`는
실행 중에 바꾸면 다음 프레임부터 반영된다 (19강 트랙바 대신 `rqt_reconfigure` 슬라이더 / `ros2 param set`).

## 3.5 값 찾기 (튜닝, 기록 없음)

```bash
# 터미널 1: 검출 노드 하나 (출력 /hsv/*)
ros2 launch hsv_detector detector.launch.py config:=base.yaml ns:=hsv \
    image_topic:=/camera/color/jpeg input_compressed:=true
# 터미널 2: 입력 bag 반복 재생
ros2 bag play ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/bags/BAG-LOST --topics /camera/color/jpeg --loop
# 터미널 3: 화면 — /hsv/mask, /hsv/image_annotated
ros2 run rqt_image_view rqt_image_view
# 터미널 4: 값 바꾸기 (슬라이더)
ros2 run rqt_reconfigure rqt_reconfigure            # /hsv/color_detector 선택
#   또는 한 줄씩
ros2 param set /hsv/color_detector s_lo 80
ros2 param set /hsv/color_detector min_area 800.0   # float 파라미터는 소수점 필요
ros2 topic echo /hsv/detection_stats --field data   # 후보 수·mask 픽셀 수 확인
# 정한 값 확인
ros2 param dump /hsv/color_detector
```

정한 값은 `config/*.yaml`에 옮겨 적고 `colcon build` 후 4절에서 기록한다.
RAW-01로 볼 때는 `image_topic:=/camera/camera/color/image_raw input_compressed:=false`, play 쪽 `--topics`도 같이 바꾼다.

## 4. 실험 실행 (예: 실험 1, BAG-LOST)

같은 재생을 두 노드(/A, /B)가 함께 받으므로 A와 B의 입력 프레임이 같다. `bag_tools summary`가 공통 stamp 수로 확인해 준다.

```bash
# 터미널 1: 검출 노드 A/B
ros2 launch hsv_detector detector.launch.py config:=exp1_A.yaml config_b:=exp1_B.yaml \
    image_topic:=/camera/color/jpeg input_compressed:=true

# 터미널 2: 출력 기록
ros2 bag record -o ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/out/exp1 -e '/(A|B)/.*'

# 터미널 3: 입력 재생 (이미지 토픽만)
ros2 bag play ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/bags/BAG-LOST --topics /camera/color/jpeg
# 재생이 끝나면 터미널 2·1 Ctrl+C

# 확인 (실행 중): ros2 topic list / ros2 topic hz /A/detection_stats / rqt_image_view 로 /A/mask, /B/mask
```

| 실험 | config | config_b | 입력 bag | image_topic | input_compressed |
|---|---|---|---|---|---|
| 실험 1 (HSV Mask) | exp1_A.yaml | exp1_B.yaml | BAG-LOST | /camera/color/jpeg | true |
| 실험 2 (min_area) | exp2_A.yaml | exp2_B.yaml | RAW-01 | /camera/camera/color/image_raw | false |
| no-target 확인 | base.yaml (단일, ns=hsv) | — | BAG-OK | /camera/color/jpeg | true |

## 5. 집계·이미지 추출

```bash
# 프레임 수·검출률·후보 수·면적, A/B면 같은 stamp 비교와 갈린 프레임 시각까지
ros2 run hsv_detector bag_tools summary ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/out/exp1
ros2 run hsv_detector bag_tools summary ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/out/notarget --t0 3 --t1 28   # 구간 집계

# 지정 시각 비교 이미지 (한 시각 = 한 장: 위 Raw·Mask, 아래 검출)
ros2 run hsv_detector bag_tools export ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/out/exp1 ~/physicalai-lv2-JunmyeongPark/lv2_module3/results/exp1 \
    --at 8.0 14.04 19.25 22.25 26.05 --prefix exp1
ros2 run hsv_detector bag_tools export ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/out/exp2 ~/physicalai-lv2-JunmyeongPark/lv2_module3/results/exp2 \
    --at 1 9 17 --prefix exp2
ros2 run hsv_detector bag_tools export ~/physicalai-lv2-JunmyeongPark/lv2_module3/hsv_ws/out/notarget ~/physicalai-lv2-JunmyeongPark/lv2_module3/results/no_target \
    --at 3 10 20 28 40 --prefix notarget
```

- Raw·검출 이미지는 JPEG 사본(`…/compressed`), Mask는 mono8 원본에서 꺼낸다. bgr8 원본 토픽은 장당 약 690 KB라 기록 중 빠질 수 있어 쓰지 않는다.
- rqt에서 컬러 이미지가 끊기면 `ros-jazzy-image-transport-plugins`를 설치하고 `…/image_annotated/compressed`를 본다.
- `summary` 출력과 `export` 이미지를 `results/`에 넣고 report.md 표에 옮긴다.
