# 모듈3 추가과제 — HSV Mask·검출 설정값 비교 실험

- 작성자: 박준명 ([JunmyeongPark](https://github.com/JunmyeongPark))
- 코드: [`hsv_ws/`](hsv_ws/) (실행 방법: [`hsv_ws/README.md`](hsv_ws/README.md))
- 결과: [`results/`](results/)

> **입력 조건: 실시간 카메라가 아니라 기록된 rosbag 재생이다.**
> - 실험 1(BAG-LOST)과 no-target 확인(BAG-OK)의 입력은 **5 Hz JPEG**(`sensor_msgs/CompressedImage`, 프레임 간격 0.2 s)이다. 팀 프로젝트(2026-10-08) 녹화 조건 그대로이며, 화면이 0.2 s마다 바뀌는 것은 입력 때문이다.
> - 실험 2(RAW-01)의 입력은 약 30 Hz 원본 `sensor_msgs/Image`(rgb8, 640x360)이다.
> - 검출 노드 자체의 처리 시간은 입력 주기와 별개로 노드 로그·`detection_stats`의 처리 시간으로 따로 기록한다.

> 모든 수치는 ROS 2 토픽(`detection_stats`)을 기록한 bag에서 `bag_tools summary`로 집계한 값이고, 이미지는 같은 bag에서 `bag_tools export`로 뽑았다. 추정값은 넣지 않았다.

## 1. 개요

- 목적: 같은 입력에서 설정값 하나만 바꿨을 때 Mask와 검출 결과가 어떻게 달라지는지 확인한다.
  - 실험 1: HSV Mask 범위 A vs B
  - 실험 2: HSV 고정, 후보 필터 `min_area` A vs B
  - 추가: 대상이 없는 구간(no-target)에서 오검출 여부
- 검출기: 19강 `ColorDetector`를 수정 없이 사용하고, 21강 구조(cv_bridge 노드)로 ROS 2 토픽에 연결했다. 새 검출 알고리즘이나 모터 제어는 없다.
- 증빙: Raw Image(`image_input`), Mask(`mask`), 검출(`detection`, `detection_stats`)을 ROS 2 토픽으로 받아 bag으로 기록하고, 그 bag에서 수치와 이미지를 뽑았다. OpenCV 로컬 창은 증빙으로 쓰지 않았다.

## 2. 실행 환경

| 항목 | 값 |
|---|---|
| PC / OS | Legion Pro 5 16IAX10 (호스트명 기준) / Ubuntu 24.04.5 LTS (kernel 7.0.0-34-generic) |
| Python | 3.12.3 (노드 시작 로그) |
| OpenCV | 4.6.0 (노드 시작 로그, `cv2.__version__`) |
| ROS 2 | Jazzy (노드 시작 로그 `ROS_DISTRO=jazzy`) |
| cv_bridge | ros-jazzy-cv-bridge 4.1.0 |
| rosbag2 | ros-jazzy-rosbag2 0.26.11 |
| 입력 방식 | rosbag 재생 (실시간 카메라 아님) |

## 3. 입력 데이터 (rosbag)

팀 프로젝트(Lv2 모듈5, 팀 Live.Eat)에서 2026-10-08 실기 시험 때 TurtleBot3 Waffle Pi(Raspberry Pi 4) + RealSense D435로 기록한 bag을 재사용했다. **실시간 카메라 입력이 아니라 기록된 bag 재생 결과다.**

- 출처: 팀 Google Drive [`bags/`](https://drive.google.com/drive/folders/1R_BAn832ETpi6gQRwt-JQcdjtKF2fso_) (로컬 사본: `bags-20261008T082834Z-1-001.zip`)
- 저장 형식: mcap. 저장소에는 올리지 않음(용량). 무결성 확인은 sha256.

| bag | 파일 | 이미지 토픽 / 타입 | 프레임 수 · 길이 | 장면 | sha256 (앞 8자리) | 사용 |
|---|---|---|---|---|---|---|
| RAW-01 | `0_bag_2026_10_08-05_46_28.mcap` | `/camera/camera/color/image_raw` / Image rgb8 640x360 | 542 · 약 18 s | 상자 위 고정된 파란 퍽, 카메라 정지 | `6f36df83` | 실험 2 |
| BAG-LOST | `0_bag_2026_10_08-05_30_55.mcap` | `/camera/color/jpeg` / CompressedImage, 5 fps | 150 · 약 30 s | 손에 든 퍽, 상자 가림·재등장, 역광·형광등 | `917cfb62` | 실험 1 |
| BAG-OK | `0_bag_2026_10_08-05_17_38.mcap` | `/camera/color/jpeg` / CompressedImage, 5 fps | 268 · 약 54 s | 앞 구간: 발·바닥만(퍽 없음), 뒤 구간: 손에 든 퍽·바닥 위 퍽 | `961f6c0f` | no-target |

관찰 구간 (첫 입력 프레임 stamp 기준 상대 시간):

| 용도 | bag | 구간 | 근거 |
|---|---|---|---|
| 실험 1 | BAG-LOST | 전체 (0 ~ 끝) | — |
| 실험 2 | RAW-01 | 전체 (0 ~ 끝) | — |
| no-target | BAG-OK | 3 ~ 28 s | 팀 YOLO `/detection`이 약 2.0 ~ 29.1 s 동안 미검출이었던 기록에 앞뒤 약 1 s 여유를 두고, 구간 안 프레임에 퍽이 없는 것을 육안 확인 (7절) |

## 4. 검출 파이프라인과 설정

```
Image / CompressedImage ──cv_bridge──> BGR
  └─ make_mask: GaussianBlur(5) → HSV → inRange(lo, hi) → OPEN(5) → CLOSE(5)        ──> /…/mask
  └─ detect:   findContours → ① area ≥ min_area → ② circularity ≥ min_circularity
               → 최대 면적 1개 → 모멘트 중심 → EMA(α)                                ──> /…/detection, /…/detection_stats
  └─ draw_overlay                                                                     ──> /…/image_annotated
```

공통 설정 (`config/base.yaml`):

| 파라미터 | 값 | 이유 |
|---|---|---|
| hsv_lo / hsv_hi | [100, 120, 40] / [125, 255, 255] | 파란 퍽 H 대역, S 하한으로 물빠진 배경 제거, V 하한으로 그림자 제거 |
| min_area | 300 px² | 점 노이즈 제거 |
| min_circularity | 0.3 | 퍽 측면은 직사각형이고 손에 일부 가려지므로 공 기준(0.6)보다 낮춤 |
| ema_alpha | 0.3 | 중심 떨림 완화. 미검출 프레임은 None |
| QoS | 입력 reliable depth 50 (bag 재생 시) / 수치 출력(`detection`, `detection_stats`) reliable depth 10 / 이미지 출력 best-effort depth 5 + JPEG 사본(`…/compressed`) | 입력·수치는 A·B가 같은 프레임을 빠짐없이 받고 남기도록. 이미지는 느린 뷰어가 노드를 붙잡지 않도록 (21강 4절) |

A/B는 같은 bag 재생을 두 노드(`/A`, `/B`)가 동시에 구독하는 방식으로 돌렸다. 같은 입력이었는지는 `bag_tools summary`의 공통 stamp 수로 확인한다.

## 5. 실험 1 — HSV Mask 범위 A vs B

| | A (`exp1_A.yaml`) | B (`exp1_B.yaml`) |
|---|---|---|
| hsv_lo | [100, 120, 40] | [90, 60, 30] |
| hsv_hi | [125, 255, 255] | [130, 255, 255] |
| 나머지 | base와 같음 | base와 같음 |
| 입력 | BAG-LOST 전체 | BAG-LOST 전체 |

결과 (`ros2 run hsv_detector bag_tools summary hsv_ws/out/exp1`, 2026-10-12 실행):

| | A | B |
|---|---|---|
| 처리 프레임 수 | 150 | 150 |
| 공통 stamp 수 (같은 입력 확인) | 150 / 150 | ← |
| 검출 프레임 수 / 검출률 | 119 / 0.793 | 130 / 0.867 |
| 평균 mask 픽셀 수 | 1735 | 3018 |
| 평균 컨투어 수 (필터 전) | 0.97 | 4.31 |
| 평균 면적 필터 통과 수 | 0.79 | 1.48 |
| 평균 형상 필터 통과 수 | 0.79 | 1.14 |
| 평균 처리 시간 [ms] (mask + detect) | 0.77 | 0.79 |

A·B 프레임별 비교 (`detection_stats` 150쌍, 같은 stamp끼리 비교):

| 구분 | 프레임 수 |
|---|---|
| A·B 모두 검출, 중심 차이 30 px 이하 (같은 대상) | 109 |
| A·B 모두 검출, 중심 차이 30 px 초과 (다른 대상) | 10 |
| B만 검출 | 11 |
| A만 검출 | 0 |
| 둘 다 미검출 | 20 |

A·B가 갈린 21프레임 육안 판정 (`results/exp1/exp1_AB_diff_21frames.jpg`, 각 칸 왼쪽 A·오른쪽 B 오버레이):

| 구분 | 시각 [s] | 판정 |
|---|---|---|
| 다른 대상 10프레임 | 7.61, 8.00, 25.45 ~ 26.85 (8프레임) | A는 퍽, **B는 검은 바지** — B의 Mask에 바지 덩어리가 들어오고 퍽보다 커서 최대 면적 후보가 바뀜 |
| B만 검출 11프레임 중 퍽 | 19.25, 28.05 | 손에 가려 A Mask가 면적 하한(300 px²) 아래로 줄어든 퍽을 B가 잡음 (A 19.25 s mask 329 px) |
| B만 검출 11프레임 중 퍽 아님 | 14.04, 14.44, 15.04, 21.65, 22.25, 28.65, 29.45, 29.65, 29.85 | 바지·슬리퍼·옷, 바닥의 파란 선(22.25 s) |

> 판정은 작성자가 ROS로 기록한 `image_annotated/compressed`를 보고 한 육안 판정이다. A·B가 같은 대상을 잡은 109프레임과 둘 다 미검출인 20프레임은 이 표에서 따로 판정하지 않았다.

대표 이미지 (`results/exp1/`, 각 파일 = 위: Raw · A mask · B mask / 아래: A 검출 · B 검출):

| 시각 [s] | 파일 | A | B | 내용 |
|---|---|---|---|---|
| 8.00 | [`exp1_t008.00.png`](results/exp1/exp1_t008.00.png) | 퍽 (mask 1160 px) | 바지 (mask 3797 px) | B Mask에 바지가 추가돼 대상이 바뀜 |
| 14.04 | [`exp1_t014.04.png`](results/exp1/exp1_t014.04.png) | 미검출 (mask 0 px) | 바지 | 퍽이 손에 가려 안 보이는 프레임에서 B 오검출 |
| 19.25 | [`exp1_t019.25.png`](results/exp1/exp1_t019.25.png) | 미검출 (mask 329 px, 면적 필터 탈락) | 퍽 | B가 가려진 퍽을 살림 |
| 22.25 | [`exp1_t022.25.png`](results/exp1/exp1_t022.25.png) | 미검출 (mask 0 px) | 바닥 파란 선 | 퍽이 없는 프레임에서 B 오검출 |
| 26.05 | [`exp1_t026.05.png`](results/exp1/exp1_t026.05.png) | 퍽 (mask 2834 px) | 바지 (mask 6609 px) | B는 퍽도 Mask에 있지만 더 큰 바지를 선택 |

해석:
- B는 H·S·V 하한을 모두 낮춰 평균 Mask 픽셀이 1735 → 3018 px(약 1.7배), 필터 전 컨투어가 0.97 → 4.31개로 늘었다. 늘어난 픽셀은 대표 이미지에서 퍽이 아니라 검은 바지·슬리퍼·바닥 선처럼 어둡고 채도가 낮은 영역이었다.
- B의 검출률(0.867)은 A(0.793)보다 높지만, A와 갈린 21프레임 중 B가 맞게 잡은 것은 2프레임(가려진 퍽)뿐이고 나머지 19프레임은 다른 물체였다. 검출률만 보면 B가 나아 보이지만 실제로는 오검출과 대상 바뀜이 늘었다.
- 원인은 검출기가 필터를 통과한 후보 중 **가장 큰 덩어리 1개**를 고르는 구조라서, Mask가 넓어져 배경 덩어리가 퍽보다 커지면 퍽이 Mask 안에 있어도 대상이 바뀐다는 점이다(26.05 s).
- 따라서 이 입력에서는 A처럼 S·V 하한을 높여 어두운 배경을 먼저 걸러내는 쪽이 맞다. B의 이득(가려진 퍽 2프레임)은 손에 가려 작아진 퍽이 A에서 면적 하한 아래로 떨어진 경우라, 대상 크기와 면적 필터의 관계는 실험 2에서 따로 본다.

증빙 참고: 원본 bgr8 이미지 토픽(`image_input`, `image_annotated`)은 장당 약 690 KB라 같은 PC 안에서도 기록 중 대부분 빠졌다(`/A/image_input` 150 중 9개 기록). 수치(`detection_stats` 150/150)와 Mask(150/150), JPEG 사본(`…/compressed` 150/150)은 모두 기록되어, 이미지 증빙은 JPEG 사본과 Mask에서 뽑았다.

## 6. 실험 2 — min_area A vs B (HSV 고정)

| | A (`exp2_A.yaml`) | B (`exp2_B.yaml`) |
|---|---|---|
| HSV | base와 같음 | base와 같음 |
| min_area | 300 px² | 1500 px² |
| 입력 | RAW-01 전체 | RAW-01 전체 |

결과 (`ros2 run hsv_detector bag_tools summary hsv_ws/out/exp2`, 2026-10-12 실행):

| | A | B |
|---|---|---|
| 처리 프레임 수 | 542 | 542 |
| 공통 stamp 수 (같은 입력 확인) | 542 / 542 | ← |
| 검출 프레임 수 / 검출률 | 542 / 1.000 | 0 / 0.000 |
| 평균 mask 픽셀 수 | 727 | 727 (HSV 같음) |
| 평균 컨투어 수 (필터 전) | 1.00 | 1.00 |
| 평균 면적 필터 통과 수 | 1.00 | 0.00 |
| 평균 형상 필터 통과 수 | 1.00 | 0.00 |
| 검출 시 퍽 컨투어 면적 (min / median / max) | 663 / 672 / 684 px² | — |
| 평균 처리 시간 [ms] (mask + detect) | 0.52 | 0.63 |

A·B 프레임별 비교: A만 검출 542, 그 외 0.

이미지 (`results/exp2/`, 각 파일 = 위: Raw · A mask · B mask / 아래: A 검출 · B 검출):

| 시각 [s] | 파일 | A | B |
|---|---|---|---|
| 1.00 | [`exp2_t001.00.png`](results/exp2/exp2_t001.00.png) | 퍽 검출 (area 667) | 미검출 (같은 Mask 721 px) |
| 9.01 | [`exp2_t009.01.png`](results/exp2/exp2_t009.01.png) | 퍽 검출 (area 670) | 미검출 (같은 Mask 724 px) |
| 17.01 | [`exp2_t017.01.png`](results/exp2/exp2_t017.01.png) | 퍽 검출 (area 674) | 미검출 (같은 Mask 728 px) |

세 장 모두 A·B의 Mask는 퍽 하나만 흰색으로 같고, B는 그 퍽을 면적 필터에서 버렸다. 17.01 s에는 화면 왼쪽에 발(검은 바지·슬리퍼)이 들어왔지만 기본 HSV 범위(S ≥ 120)에서는 Mask에 나타나지 않았다.

해석:
- HSV가 같으므로 A·B의 Mask는 같고(평균 727 px, 프레임마다 컨투어 1개), 차이는 면적 필터에서만 생겼다.
- 이 장면의 퍽 컨투어 면적은 전 구간 663 ~ 684 px²였다. B의 하한 1500 px²는 퍽보다 커서 **진짜 대상을 모든 프레임에서 버렸다**(542 → 0). A의 하한 300 px²는 퍽보다 작아 모두 통과했다.
- 이 입력에는 퍽 말고 다른 컨투어가 없어(필터 전 평균 1.00개) A의 낮은 하한이 노이즈를 더 통과시키는 손해는 나타나지 않았다. 즉 이 실험은 "하한이 대상보다 크면 미검출"만 보여 주고, "하한이 너무 작으면 노이즈 통과"는 보여 주지 못한다.
- min_area는 대상이 가장 작게 보이는 경우(가장 먼 거리, 손에 일부 가린 경우)보다 작아야 한다. 실험 1의 19.25 s처럼 손에 가린 퍽은 Mask가 329 px까지 줄어 300 px² 하한에도 걸렸으므로, 고정값 하나로는 거리·가림 변화에 모두 맞추기 어렵다(19강: 거리 적응형 min_area).

## 7. no-target 확인

| 항목 | 값 |
|---|---|
| 설정 | base.yaml (실험 1·2의 A와 같은 HSV, min_area 300) |
| 입력 | BAG-OK 전체 재생, 노드가 처리한 프레임 266 / bag 268 (처음 2프레임은 구독 연결 전에 지나감) |
| 관찰 구간 | 3 ~ 28 s (첫 처리 프레임 stamp 기준) |
| 구간 프레임 수 | 125 |
| 검출(오검출) 프레임 수 | **0** (검출률 0.000) |
| 평균 mask 픽셀 수 | 0 |
| 평균 컨투어 수 (필터 전) | 0.00 |
| 참고: bag 전체 | 266프레임 중 129 검출 (구간 밖 퍽이 보이는 장면), 검출 면적 1116 / 2350 / 6850 px² (min / median / max) |

구간 확인 근거: 팀 YOLO `/detection`이 같은 bag에서 약 2.0 ~ 29.1 s 동안 미검출이었던 기록, 그리고 아래 구간 안 4장(3.00 / 10.11 / 19.91 / 27.92 s)에 퍽이 없고 발·바닥·상자만 보이는 것을 육안으로 확인했다. 구간 125프레임 전체를 한 장씩 보지는 않았다.

이미지 (`results/no_target/`, 각 파일 = 위: Raw · Mask / 아래: 검출):

| 시각 [s] | 파일 | 장면 | 결과 |
|---|---|---|---|
| 3.00 | [`notarget_t003.00.png`](results/no_target/notarget_t003.00.png) | 발·슬리퍼·바닥 | mask 0 px, 미검출 |
| 10.11 | [`notarget_t010.11.png`](results/no_target/notarget_t010.11.png) | 같음 | mask 0 px, 미검출 |
| 19.91 | [`notarget_t019.91.png`](results/no_target/notarget_t019.91.png) | 같음 | mask 0 px, 미검출 |
| 27.92 | [`notarget_t027.92.png`](results/no_target/notarget_t027.92.png) | 같음 | mask 0 px, 미검출 |
| 39.93 | [`notarget_t039.93.png`](results/no_target/notarget_t039.93.png) | 구간 밖, 손에 든 퍽 (대조용) | mask 2434 px, 퍽 검출 (area 2336) |

해석:
- 기본 설정에서는 퍽이 없는 25 s 동안 Mask 픽셀이 한 번도 생기지 않아 오검출 0이었다. 같은 장면의 검은 바지·슬리퍼·종이 상자는 S ≥ 120 하한에서 모두 걸러졌다.
- 실험 1의 B처럼 S·V 하한을 낮추면 같은 종류의 장면(바지·슬리퍼)에서 오검출이 생겼으므로(5절), no-target 결과는 HSV 하한 설정에 달려 있다.
- 미검출 프레임에서 노드는 `detection`을 발행하지 않고 `detection_stats`에 `detected: false`만 남긴다(마지막 위치를 유지하지 않음).

## 8. 결론·한계

- 결론
  - **HSV Mask 범위 (실험 1):** 범위를 넓히면(B) 검출률은 0.793 → 0.867로 올랐지만, A와 갈린 21프레임 중 19프레임이 바지·슬리퍼·바닥 선 같은 다른 물체였다. 검출률만으로는 Mask 설정의 좋고 나쁨을 판단할 수 없고, 같은 프레임에서 무엇을 잡았는지 함께 봐야 한다. 이 입력에서는 S·V 하한을 높인 A가 맞는 설정이다.
  - **min_area (실험 2):** HSV가 같으면 Mask는 같고, min_area는 그 Mask의 덩어리 중 무엇을 후보로 남길지만 바꾼다. 하한(1500 px²)이 대상 크기(663 ~ 684 px²)보다 크면 대상이 매 프레임 사라진다(542 → 0). 하한은 대상이 가장 작게 보이는 경우보다 작게 잡아야 한다.
  - **no-target:** 기본 설정(A)에서 퍽이 없는 125프레임 동안 오검출 0, Mask 0 px였다.
- 한계
  - 입력이 기록된 bag 3개뿐이고, 조명·배경 조건을 일부러 바꿔 가며 찍은 시험 영상은 아니다.
  - BAG-LOST·BAG-OK는 JPEG 압축 입력이라 압축 노이즈가 Mask 경계에 영향을 줄 수 있다.
  - 단일 대상(파란 퍽)만 다뤘다.
  - 실험 2 입력(RAW-01)에는 퍽 외 컨투어가 없어, min_area를 낮췄을 때 노이즈가 통과하는 쪽의 효과는 확인하지 못했다.
  - 실험 1의 육안 판정은 A·B가 갈린 21프레임에 대해서만 했다. 같은 대상을 잡은 109프레임이 모두 퍽인지는 따로 판정하지 않았다.
  - bgr8 원본 이미지 토픽은 장당 약 690 KB라 기록 중 대부분 빠졌다. 이미지 증빙은 JPEG 사본과 Mask로 대신했다.

## 9. 재현

[`hsv_ws/README.md`](hsv_ws/README.md)의 1 ~ 5절 순서대로 실행하면 된다.
