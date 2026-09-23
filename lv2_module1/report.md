# 모듈 1 과제 보고서

- 이름: 박준명
- 제출 범위: 문제 1 — 원격 환경 구성과 모터 응답 확인

## 문제 1

### 1. 장비 및 원격 환경

라즈베리파이에 Ubuntu Server 22.04를 구성하고 PC에서 SSH로 접속하는 환경을 준비했다. OpenCR 1.0은 라즈베리파이에 USB로 연결하며, 펌웨어 업로드와 시리얼 송수신·로그 저장은 라즈베리파이에서 수행하는 구성이다. 다이나믹셀은 1개를 사용한다.

| 항목 | 실제 환경 및 확인 상태 |
|---|---|
| 라즈베리파이 호스트명 | `pa01` — `hostname` 출력 확인 |
| Ubuntu 버전 | Ubuntu 22.04.5 LTS (Jammy Jellyfish) — `/etc/os-release` 확인 |
| 아키텍처 | `aarch64` — `uname -m` 출력 확인 |
| 실행 사용자·포트 접근 그룹 | `pa01` (UID/GID 1000), `dialout` 그룹 소속 확인 |
| OpenCR 포트 및 접근 권한 | `/dev/ttyACM0`, 115200 bps로 miniterm 접속·응답 수신 확인. 장치 권한 `crw-rw----`, 소유자 `root`, 그룹 `dialout` ([확인 출력](results/upload_precheck.log)) |
| 모터 모델·ID | XM430-W210 (모델 번호 `1030`), ID `1` — 진단 스캔 응답 및 공식 모델 표 기준 |
| 모터 통신 속도·프로토콜·펌웨어 버전 | 1 Mbps, Protocol 2.0. 모터 펌웨어 버전은 미확인 |

진단 증거: [diagnostic_scan.log](results/diagnostic_scan.log). 사용자가 제공한 터미널 출력을 저장했다. `OPENCR_DIAGNOSTIC_V1`의 응답과 모터 검색 성공을 확인했으며, 진단 코드는 모터 설정 변경·구동 명령을 보내지 않는다. 시작 부분에 `Command too long`이 있었으나 이후 스캔은 `FOUND`와 `SCAN_DONE`으로 완료됐다.

이 진단 코드는 모델 번호가 1020일 때만 펌웨어 버전 등의 추가 항목을 읽으므로, 이번 출력에 해당 항목이 없는 것은 코드의 분기 조건에 따른 것이다.

환경 증거: [results/환경확인.txt](results/환경확인.txt). 사용자 제공 출력을 명령별로 구분해 저장했으며, 채팅에서 링크로 표시된 OS 정보의 URL은 일반 문자열로 복원했다.

### 2. 펌웨어 빌드·업로드 및 실행 설정

제공 예제를 복사한 [수정 P 제어 소스](examples/opencr_position_p/opencr_position_p.ino)를 사용한다. 원본은 XM430-W350(모델 1020)·ID 12 기준이며, 진단 결과와 [ROBOTIS 공식 모델 표](https://emanual.robotis.com/docs/kr/dxl/x/xm430-w210/)에 맞춰 다음을 수정했다.

- `DXL_ID`: `12` → `1`.
- 모델 검사: `XM430_W350` → `XM430_W210` (모델 1030). 오류 메시지 및 장비 주석도 수정.
- 1 Mbps, Protocol 2.0, 펌웨어 버전 38 이상·Drive Mode 검사, 제어 계산 및 정지 처리는 유지.

라즈베리파이 `pa01`에서 수정 소스를 Arduino CLI로 빌드했고, 사용자가 제공한 성공 출력을 [build.log](results/build.log)에 저장했다. 이 파일은 제공된 출력 2행을 보존한 것으로 전체 빌드 로그는 아니다.

| 빌드 항목 | 설정 또는 결과 |
|---|---|
| 소스 경로 | `~/opencr-diagnosis/opencr_position_p` |
| 보드 FQBN | `ROBOTIS:OpenCR:OpenCR` |
| 병렬 작업 수 | `--jobs 1` |
| 프로그램 저장 공간 | 104,296 bytes / 786,432 bytes (13%) |
| 전역 변수 메모리 | 40,620 bytes |
| 출력 디렉터리 | `/home/pa01/opencr-diagnosis/build-20260921-172723` — 업로드 전 확인 출력 기준 |
| `.bin` 파일 확인 | `ls -lh` 출력에서 103K 파일 확인. [확인 출력](results/build_artifact.log) |

실행한 빌드 명령:

```bash
export OPENCR_BUILD="$HOME/pa-opencr-build"
export OPENCR_OUTPUT="$HOME/opencr-diagnosis/build-$(date +%Y%m%d-%H%M%S)"
set -o pipefail

"$OPENCR_BUILD/bin/arduino-cli" \
  --config-file "$OPENCR_BUILD/arduino-cli.yaml" \
  compile \
  --fqbn ROBOTIS:OpenCR:OpenCR \
  --jobs 1 \
  --output-dir "$OPENCR_OUTPUT" \
  "$HOME/opencr-diagnosis/opencr_position_p" \
  2>&1 | tee "$HOME/opencr-diagnosis/build.log"
```

빌드 성공과 생성된 `.bin` 파일의 존재(표시 크기 103K)를 사용자 제공 출력으로 확인했다. 최초 [파일 확인 출력](results/build_artifact.log)의 경로는 일부만 전달되었으며, 이후 [업로드 전 확인 출력](results/upload_precheck.log)에서 전체 경로를 확인했다. 라즈베리파이에서 업로드 성공을 확인했으며, `READY` 출력은 미확보지만 정상 설정 응답, 실행 A 측정값과 사용자 정지 응답을 확보했다. 업로드에는 기존 제공 바이너리가 아닌 이번 빌드 결과를 사용한다. 진단 응답과 빌드 성공은 P 제어 펌웨어의 업로드 성공 또는 실행 A 증거를 대신하지 않는다.

업로드 전 파일 및 포트 확인 결과:

| 항목 | 확인 내용 |
|---|---|
| 업로더 | `/home/pa01/pa-opencr-build/uploader-src/arduino/opencr_develop/opencr_ld/opencr_ld` |
| 업로더 권한·크기 | `-rwxrwxr-x`, 38,856 bytes |
| 업로드 대상 파일 | `/home/pa01/opencr-diagnosis/build-20260921-172723/opencr_position_p.ino.bin` |
| 대상 파일 권한·크기 | `-rwxrwxr-x`, 103K (`ls -lh` 표시) |
| OpenCR 포트 | `/dev/ttyACM0`, `root:dialout`, `crw-rw----` |

위 결과는 업로드 전 확인 기록이다. 이후 라즈베리파이에서 다음 명령으로 업로드했고, 사용자가 제공한 출력을 [upload.log](results/upload.log)에 저장했다.

```bash
set -o pipefail
"$UPLOADER" /dev/ttyACM0 115200 \
  "$OPENCR_OUTPUT/opencr_position_p.ino.bin" 1 \
  2>&1 | tee "$HOME/opencr-diagnosis/upload.log"
```

업로더 버전은 `opencr_ld 1.0.4`, 인식된 보드는 `OpenCR R1.0`이다. `CRC OK 9B81E2 9B81E2`와 `[OK] Download`로 업로드 성공을 확인했으며 `jump finished`까지 출력됐다. 펌웨어의 `READY` 출력은 미확보이며, 이후 정상 설정 응답과 실행 A 로그로 명령 처리 및 측정을 확인했다. 업로더의 파일 크기 표시는 `102 KB`이며, 앞선 `ls -lh`의 표시는 `103K`였다.

| 항목 | 실행 A 기록 |
|---|---|
| 업로드한 펌웨어 파일 | `/home/pa01/opencr-diagnosis/build-20260921-172723/opencr_position_p.ino.bin` |
| 라즈베리파이에서 업로드 성공 | `CRC OK 9B81E2 9B81E2`, `[OK] Download`, `jump finished` 확인 |
| 펌웨어 준비 응답 | `READY` 출력은 미확보. `k 0.5`에 대한 정상 `P SET` 응답 확인 ([settings.log](results/settings.log)) |
| OpenCR 위치 제어 Kp (1/s) | `0.5` — 설정 응답 및 실행 A의 `kp:0.5000` 확인 |
| 상대 목표각 (°) | `10` — 실행 A의 `target_deg:10.000` 확인 |
| 속도 상한 (°/s) | `5` — 실행 A의 `v_limit_deg_s:5.000` 확인 |
| 실행 명령 | 안내 명령은 `s 0.5 5 10`. 제공된 발췌에 명령·START 행은 없으며, 설정값은 측정 로그로 확인 |

Kp는 OpenCR에서 위치 오차를 목표 각속도로 변환하는 P 제어 게인이다. 다이나믹셀 내부 위치 게인과 구분하며, 제공 예제에서 I항과 D항은 0이다.

업로드 증거: [results/upload.log](results/upload.log). 실제 업로드 성공 출력을 저장했다. `READY` 출력은 확보하지 못했으나 정상 `P SET` 응답과 실행 A 측정 로그를 확보했다.

### 3. 목표값·측정값·제어 출력

아래는 실행 A 로그를 해석하기 위한 필드 정의다.

| 구분 | 로그 필드 | 의미 | 단위 |
|---|---|---|---|
| 목표값 | `target_deg` | 시작 위치 기준 상대 목표각. 시작 후 2초 동안 0°이고 이후 설정한 목표각 적용 | ° |
| 측정값 | `position_deg` | 엔코더 위치에서 계산한 시작 위치 기준 상대각 | ° |
| 오차 | `error_deg` | 목표각 − 현재각 | ° |
| P 계산값 | `p_deg_s` | Kp × 위치 오차. 코드의 데드밴드 내에서는 0 | °/s |
| 제어 출력 | `u_deg_s` | 속도 제한 및 raw 단위 변환을 거쳐 모터에 전달한 목표 각속도 | °/s |
| 측정 속도 | `speed_deg_s` | 모터에서 읽은 실제 각속도 | °/s |
| 제어 간격 | `dt_ms` | 실제 제어 루프 사이 시간 | ms |
| 경과 시간 | `t_s` | 실행 시작 이후 시간 | s |

실행 증거: [results/실행A.log](results/실행A.log). 첨부 파일을 내용 변경 없이 저장했다. 0.200~12.402초의 측정값 123행, 목표가 10°로 변경된 이후 105행, `xSTOP: user` 및 터미널 종료 기록을 포함한다. 실행 명령·START·READY 행은 첨부에 없으며, 정지 명령의 정확한 경과 시간도 출력되지 않았다. 2.000초 행은 일부 필드 사이 탭이 없지만 필드명과 값은 식별할 수 있어 아래 표에 그대로 반영했다.

| 경과 시간 (s) | 목표각 (°) | 현재각 (°) | 오차 (°) | P 계산값 (°/s) | 제어 출력 (°/s) | 측정 속도 (°/s) | 제어 간격 (ms) |
|---|---|---|---|---|---|---|---|
| 2.000 | 10.000 | -0.088 | 10.088 | 5.044 | 4.122 | 0.000 | 10.000 |
| 3.000 | 10.000 | 3.604 | 6.396 | 3.198 | 2.748 | 2.748 | 10.000 |
| 4.001 | 10.000 | 6.152 | 3.848 | 1.924 | 1.374 | 0.000 | 10.001 |
| 5.901 | 10.000 | 8.701 | 1.299 | 0.649 | 0.000 | 0.000 | 10.002 |
| 12.402 | 10.000 | 8.701 | 1.299 | 0.649 | 0.000 | 0.000 | 10.002 |

기록된 제어 간격은 10.000~10.003 ms다. 설정한 5°/s는 명령 속도의 상한이며, 코드의 raw 단위 변환 때문에 이 실행에서 최대 출력은 4.122°/s였다. 측정 속도는 별개의 피드백 값으로, 2.300초에는 5.496°/s가 기록됐다.

### 4. 결과 및 정지 확인

목표가 10°로 바뀐 2.000초에 현재각은 −0.088°였고, 목표에 가까워져 5.901초부터 마지막 측정 시각인 12.402초까지 8.701°(오차 1.299°)와 측정 속도 0°/s가 유지됐다. P 계산값 0.649°/s가 코드의 속도 명령 1단위(0.229 rpm × 6 = 1.374°/s)의 절반보다 작아 정수 변환에서 0으로 반올림되므로, 목표에 완전히 도달하기 전에 제어 출력이 0이 된 것으로 해석한다.

- 정지 명령·응답: `x` 입력 후 `STOP: user` 확인.
- 코드상 정지 처리: 목표 속도 0과 토크 해제 명령을 보내며, 두 호출이 성공한 경우 `STOP: user`를 출력한다. 이번 로그에서 해당 정상 정지 응답을 확인했다.
- 실제 정지 확인: 사용자가 `x` 입력 후 모터가 실제로 멈춘 상태였음을 확인했다. 실행 중 정지 관찰과 측정 속도 0, 이후 `STOP: user` 응답을 함께 기록했다. 토크 해제는 코드상 정상 처리 응답에 근거하며 별도 물리 측정은 하지 않았다.

환경 확인 출력과 초기·중간·마지막 응답을 포함한 실행 A 기록을 확보했다. 같은 기록을 이후 문제 2의 세 시점 비교에 재사용할 수 있다.

### 실행 전 설정 확인

`k 0.5` → `v 5` → `a 10` 순서로 설정했다. 최종 응답에서 Kp 0.5 (1/s), Ki·Kd 0, 속도 상한 5°/s, 상대 목표각 10°를 확인했다 ([settings.log](results/settings.log)). 이 응답은 실행 전 설정 확인이며 모터 실행 기록은 아니다. 해당 설정은 실행 A 측정 로그에서도 확인했다.
