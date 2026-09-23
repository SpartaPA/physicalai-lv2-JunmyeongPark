# 모듈 1 — 임베디드 제어 기초

박준명의 모듈 1 실험 환경·실행 절차와 증거 목록이다. 설정·측정·해석은 [보고서](report.md)에 정리했다.

## 환경과 소스 변경

| 항목 | 구성 |
|---|---|
| 라즈베리파이 | `pa01`, Ubuntu Server 22.04 구성, OS 출력 Ubuntu 22.04.5 LTS, `aarch64` |
| 사용자·USB 포트 | `pa01`, `dialout` 그룹 / `/dev/ttyACM0`, `root:dialout`, `crw-rw----` |
| 제어기·모터 | OpenCR 1.0 / XM430-W210(1030), ID 1, 모터 1개 |
| 통신 | USB 시리얼 115200 bps / 모터 1 Mbps, Protocol 2.0 |
| PC 역할 | SSH 접속. 업로드·시리얼 송수신·로그 저장은 라즈베리파이에서 수행 |

과제 자료의 [P 제어 예제 사본](examples/opencr_position_p/opencr_position_p.ino)을 수정했다. `DXL_ID`를 12에서 1로, 모델 검사·메시지·주석을 XM430-W350에서 XM430-W210으로 변경했다. 모델 번호 1030은 [ROBOTIS 공식 모델 표](https://emanual.robotis.com/docs/kr/dxl/x/xm430-w210/)로 확인했다. 통신 설정, 펌웨어 버전 38 이상·Drive Mode 검사, 제어 계산과 정지 처리는 유지했다.

수정 소스를 빌드·업로드한 뒤 목표각 10°, 명령 속도 상한 5°/s로 실행했다. 동일한 환경에서 Kp 0.5의 실행 A와 Kp 1.0의 실행 B를 비교했다.

## 빌드 및 업로드

다음은 라즈베리파이에 Arduino CLI와 OpenCR 코어를 설치하고 수정 소스를 `~/opencr-diagnosis/opencr_position_p`에 둔 상태에서 사용한 명령이다. 기존 제공 `.bin` 대신 수정 소스로 새로 빌드한 파일을 사용했다.

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

빌드 결과는 프로그램 104,296 bytes(13%), 전역 변수 40,620 bytes다. 실행 당시 출력 디렉터리는 `/home/pa01/opencr-diagnosis/build-20260921-172723`이었다. 이후 새 셸에서 기존 파일을 사용할 경우 `OPENCR_OUTPUT`을 이 경로로 지정한다.

업로더와 파일·포트 확인:

```bash
UPLOADER="$HOME/pa-opencr-build/uploader-src/arduino/opencr_develop/opencr_ld/opencr_ld"

if [ ! -x "$UPLOADER" ]; then
  UPLOADER="$HOME/opencr-uploader-src/arduino/opencr_develop/opencr_ld/opencr_ld"
fi

ls -l "$UPLOADER" /dev/ttyACM0
ls -lh "$OPENCR_OUTPUT/opencr_position_p.ino.bin"
```

시리얼 모니터를 종료하고 파일·포트가 확인된 상태에서 업로드했다.

```bash
set -o pipefail
"$UPLOADER" /dev/ttyACM0 115200 \
  "$OPENCR_OUTPUT/opencr_position_p.ino.bin" 1 \
  2>&1 | tee "$HOME/opencr-diagnosis/upload.log"
```

`opencr_ld 1.0.4`에서 보드 `OpenCR R1.0`을 인식했고, `CRC OK 9B81E2 9B81E2`, `[OK] Download`, `jump finished`를 확인했다. 업로더의 크기 표시는 102 KB, `ls -lh`에서는 103K였다.

## 시리얼 설정·실행·기록

라즈베리파이에서 다음 명령으로 연결했다.

```bash
python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e
```

모니터에서 `k 0.5`, `v 5`, `a 10`을 차례로 입력하고 `P SET` 응답으로 설정을 확인했다.

실행 A의 터미널 기록에는 다음 명령을 사용했다.

```bash
script -q -f -c \
  "python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e" \
  "$HOME/opencr-diagnosis/실행A.log"
```

실행 명령 형식은 `s <Kp> <속도상한_deg_s> <상대목표각_deg>`다. 실행 A는 Kp 0.5, 속도 상한 5°/s, 목표각 10°로 진행했다. 시작 위치를 0°로 삼고 2초 후 목표가 10°로 변경됐다.

실행 A에서 `x` 입력 후 `STOP: user`와 실제 모터 정지를 확인했다. 모니터는 `Ctrl+]`로 종료했다.

## 기록 범위와 해석 참고

- A 로그: 0.200~12.402초 측정 123행(목표 변경 후 105행)과 정지·종료 기록.
- B 로그: 시작·설정 응답, 0.100~9.200초 측정 92행(목표 변경 후 73행)과 정지 응답.
- 두 로그는 원문 그대로 저장했다. A의 2.000초 행은 일부 필드 사이 탭이 누락돼 필드명으로 값을 구분했다.
- `dt_ms`는 제어 간격, `t_s`는 실행 시작 이후 경과 시간이다. A·B 비교에는 시각 차이가 최대 1 ms인 표본을 사용했다.
- 명령 속도 상한 5°/s는 raw 단위 변환을 거쳐 최대 출력 4.122°/s가 됐다. 측정 속도는 별도의 피드백 값으로 A의 2.300초에는 5.496°/s가 기록됐다.

## 결과 파일

| 파일 | 내용 |
|---|---|
| [report.md](report.md) | 문제 1~4 답안 및 A·B 실측 비교 |
| [환경확인.txt](results/환경확인.txt) | 호스트명·OS·아키텍처·포트·접근 그룹 |
| [diagnostic_scan.log](results/diagnostic_scan.log) | 모델 1030·ID 1·1 Mbps·Protocol 2.0 검색 결과 |
| [build.log](results/build.log) | 수정 소스 빌드 성공 출력 |
| [build_artifact.log](results/build_artifact.log) | 최초 `.bin` 파일 확인 출력 |
| [upload_precheck.log](results/upload_precheck.log) | 업로더·포트·바이너리 전체 경로 확인 |
| [upload.log](results/upload.log) | 실제 업로드 성공 출력 |
| [settings.log](results/settings.log) | Kp 0.5·속도 상한 5°/s·목표각 10° 설정 응답 |
| [실행A.log](results/실행A.log) | 초기·중간·마지막 측정값과 `STOP: user` |
| [실행B.log](results/실행B.log) | Kp 1.0의 시작·설정 응답, 측정 92행과 `STOP: user` |

## 실행 B와 응답 비교

실행 A와 동일한 장비·설치 상태에서 외부 부하 없이 진행했다. 목표각 10°, 명령 속도 상한 5°/s, 제어 요청 주기 10 ms와 로그 주기 100 ms를 유지하고 Kp를 1.0으로 변경했다.

B 로그는 A와 별도 파일에 저장했다.

```bash
OPENCR_B_LOG="$HOME/opencr-diagnosis/실행B-$(date +%Y%m%d-%H%M%S).log"
script -q -f -c \
  "python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e" \
  "$OPENCR_B_LOG"
```

모니터에서 다음 명령을 입력했다.

```text
s 1.0 5 10
```

첫 입력은 `Invalid setting` 응답을 받아 다시 입력했고, START와 `Kp=1.0000` 설정 응답을 확인했다. 마지막 측정 시각은 9.200초이며, `x` 입력 후 `STOP: user`가 기록됐다.

공통 기록 구간의 약 3·4·6·9초 시점을 비교했다. 약 6초에서 A의 현재각은 8.701°, B는 9.316°였으며, 두 실행 모두 기록상 목표 10°를 초과하지 않았다. 상세 비교와 해석은 [보고서의 문제 3](report.md#문제-3)에 정리했다.

## 보고서 구성

- 문제 1: 환경 구성, 펌웨어 업로드, 실행 A와 정지 확인.
- 문제 2: 실행 A의 세 시점 오차, 센서·피드백 경로, 보정 방향.
- 문제 3: Kp 0.5와 1.0의 실측 응답 비교, 게인 위치와 I·D항 역할.
- 문제 4: 발제문의 가상 기록에 따른 통신 구조, 제어 주기, 통신 단절 정책.
