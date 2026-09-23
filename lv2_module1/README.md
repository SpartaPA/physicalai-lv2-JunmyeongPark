# 모듈 1 — 임베디드 제어 기초

## 수행 환경

과제에서 지정한 환경 구성을 완료했습니다.

| 항목 | 구성 |
|---|---|
| 라즈베리파이 OS·아키텍처 | Ubuntu 22.04.5 LTS, `aarch64` |
| 제어기 | OpenCR 1.0 |
| 구동 장치 | 다이나믹셀 XM430-W210 1개 — 모델 번호 1030, ID 1, 1 Mbps, Protocol 2.0 |
| 확인된 호스트·포트 | `pa01` (`hostname` 확인), `/dev/ttyACM0` (USB 시리얼 115200 bps) |
| PC 역할 | 라즈베리파이 SSH 접속 |
| USB 연결 | 라즈베리파이 ↔ OpenCR |
| 업로드·시리얼 송수신·로그 저장 위치 | 라즈베리파이 |

호스트명, 아키텍처, 사용 포트, 모터 모델·ID 등 실제 장치 정보는 [보고서](report.md)에 기록합니다. 환경 확인 출력, 업로드 성공, 실행 A 측정값 123행과 사용자 정지 응답·실제 정지 확인을 반영했습니다. 사용자 `pa01`의 `dialout` 그룹 소속도 확인했습니다.

## 진단 결과 및 적용 조건

[진단 로그](results/diagnostic_scan.log)에서 `FOUND id=1 baud=1000000 protocol=2 model=1030`을 확인했습니다. 사용자 제공 출력을 저장한 것이며, 모터 설정 변경이나 구동을 수행한 기록은 아닙니다.

현재 모터에 맞춰 [P 제어 소스](examples/opencr_position_p/opencr_position_p.ino)의 ID를 12에서 1로, 모델 검사 및 안내를 XM430-W350에서 XM430-W210으로 수정했습니다. 1 Mbps·Protocol 2.0과 기존 펌웨어 버전·Drive Mode 검사, 정지 처리는 유지했습니다. 모델 번호 1030은 [ROBOTIS 공식 문서](https://emanual.robotis.com/docs/kr/dxl/x/xm430-w210/)의 XM430-W210에 해당합니다.

라즈베리파이에서 수정 소스의 빌드 성공 출력을 확인했습니다. 프로그램 저장 공간은 104,296 bytes (13%), 전역 변수 메모리는 40,620 bytes입니다. [빌드 출력](results/build.log)은 사용자가 제공한 2행을 저장한 것이며, 추가로 `ls -lh`에서 `.bin` 파일의 존재(103K)를 확인했습니다. 후속 [업로드 전 확인 출력](results/upload_precheck.log)에서 전체 파일 경로 `/home/pa01/opencr-diagnosis/build-20260921-172723/opencr_position_p.ino.bin`, 업로더 실행 권한, `/dev/ttyACM0`의 `root:dialout` 소유 및 `crw-rw----` 권한을 확인했습니다. [업로드 로그](results/upload.log)의 `CRC OK`와 `[OK] Download`로 라즈베리파이에서 업로드 성공을 확인했습니다. `READY` 출력은 미확보지만 정상 설정 응답과 [실행 A 로그](results/실행A.log)를 확보했습니다. 목표 10°에 대해 현재각 8.701°, 잔여 오차 1.299° 및 `STOP: user`를 확인했습니다. 첨부 로그는 0.200~12.402초의 측정값 123행(목표 변경 후 105행)과 정지·종료 기록을 포함합니다. 실행 명령·START·READY 행은 첨부에 없습니다. 모터 펌웨어의 정확한 버전 번호는 미확인입니다.

## 실행 방법

1. PC에서 SSH로 라즈베리파이에 접속합니다.
2. 라즈베리파이의 OS·호스트명·아키텍처와 OpenCR 포트·접근 권한을 확인하고 `results/환경확인.txt`에 저장합니다.
3. 수정 소스의 적용 조건(XM430-W210, ID 1, 1 Mbps, Protocol 2.0, 모터 펌웨어 38 이상)을 확인하고 OpenCR용으로 빌드합니다. 기존 제공 `.bin`은 수정 사항이 반영되지 않으므로 사용하지 않습니다.
4. 새로 빌드한 펌웨어를 라즈베리파이에서 업로드하고 성공 출력과 `READY` 응답을 `results/upload.log`에 저장합니다.
5. 모터 고정, 이동 범위, 정지 방법과 전원 차단 위치를 확인한 뒤 라즈베리파이에서 USB 시리얼(115200 bps)에 연결합니다.
6. 검증된 설정으로 `s <Kp> <속도상한_deg_s> <상대목표각_deg>`와 줄바꿈을 전송합니다. 시작 위치를 0°로 삼고 2초 후 목표각이 적용됩니다. 과제 1에서는 작은 상대 목표각과 낮은 숫자 속도 상한을 사용합니다.
7. 목표 변경 이후 측정값을 5행 이상 저장하고 `x`로 정지합니다. 정지 응답과 실제 정지 여부를 확인해 `results/실행A.log` 및 보고서에 기록합니다. SSH 종료는 정지 명령이 아닙니다.

사용 소스: [examples/opencr_position_p/opencr_position_p.ino](examples/opencr_position_p/opencr_position_p.ino). 과제 자료 저장소의 동명 예제를 복사하여 장치 ID와 모델 조건을 수정했습니다.

## 결과 파일

| 경로 | 내용 | 현재 상태 |
|---|---|---|
| [report.md](report.md) | 문제 1 환경·설정·값의 단위·결과 해석 | 실행 A 설정·측정·정지 응답 및 결과 해석 반영 |
| [results/환경확인.txt](results/환경확인.txt) | 호스트명·OS·아키텍처·포트·접근 그룹 | 사용자 제공 출력 반영 완료 |
| [results/diagnostic_scan.log](results/diagnostic_scan.log) | 진단 펌웨어 응답·모터 검색 결과 | 사용자 제공 로그 반영 완료 |
| [results/build.log](results/build.log) | 수정 소스 빌드 성공 출력 2행 | 사용자 제공 출력 반영 완료 |
| [results/build_artifact.log](results/build_artifact.log) | `.bin` 파일 확인 출력 (103K) | 최초 출력 보존, 전체 경로는 후속 확인 기록 참조 |
| [results/upload_precheck.log](results/upload_precheck.log) | 업로더·포트 권한·바이너리 전체 경로 확인 | 사용자 제공 출력 반영 완료 |
| [results/upload.log](results/upload.log) | 라즈베리파이에서 업로드 성공 출력 | 업로드 성공 확인. READY 출력은 미확보, 설정·실행 응답 확보 |
| [results/settings.log](results/settings.log) | `k 0.5`, `v 5`, `a 10` 설정 응답 | 실행 전 설정 기록: Kp 0.5, 속도 상한 5°/s, 목표각 10° |
| [results/실행A.log](results/실행A.log) | 측정값 123행(목표 변경 후 105행) 및 `STOP: user` | 첨부 원문 저장, 사용자 실제 정지 확인 |

문제 2~4는 이후 같은 보고서에 추가합니다. 모듈 1 전체 문제를 완료한 뒤 최종 제출 태그 `lv2-module1-submit`을 사용합니다. 인증 정보는 제출 파일에 포함하지 않습니다.
