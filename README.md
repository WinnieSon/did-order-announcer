# 바코드 리더 시스템

시리얼 포트를 통해 바코드 데이터를 읽어 서버로 전송하는 시스템입니다.

## 프로젝트 구조

```
did-order-announcer/
├── main.py              # 메인 실행 파일
├── config.py            # 설정값들 (포트, URL, 명령어 등)
├── barcode_reader.py    # 바코드 리더 관련 기능 (시리얼 통신, 헬스체크)
├── server_client.py     # 서버 통신 관련 기능
├── monitor.py           # 시스템 상태 모니터링 (5분마다 헬스체크)
├── logging_client.py    # 시스템 로그 서버 전송 + 로컬 파일 저장 기능
└── post_backup.py       # 기존 단일 파일 백업
```

## 모듈별 역할

### config.py
- 시리얼 포트 설정 (포트명, 보드레이트)
- 서버 설정 (API URL, 호스트)
- 모니터링 간격 설정
- 헬스체크 명령어 및 응답 패턴

### barcode_reader.py
- 시리얼 포트 연결 관리
- 바코드 데이터 읽기 및 처리
- 바코드 리더기 헬스체크
- 중복 바코드 필터링

### server_client.py
- 서버 연결 상태 확인
- 바코드 데이터 서버 전송
- 서버 통신 오류 처리

### monitor.py
- 주기적 시스템 상태 모니터링 (5분마다)
- 백그라운드 스레드 관리
- 에러 상태 시 서버로 헬스 로그 전송

### logging_client.py
- 시스템 헬스 에러 로그를 서버로 전송
- **로컬 파일 로깅**: 날짜별 로그 파일 자동 생성
- **다중 로그 파일**: 전체 로그, 바코드 전용, 에러 전용 분리
- **디버그 로깅**: 시리얼 통신, 헬스체크 상세 로그
- **로그 로테이션**: 파일 크기 제한 및 백업 관리
- syslog 및 REST API 지원
- 바코드 이벤트 상세 추적 (수신/전송/중복/실패)
- 호스트명 기반 로그 식별


### main.py
- 전체 시스템 초기화 및 실행
- 각 모듈 통합 관리
- 예외 처리 및 재시도 로직



## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install pyserial requests python-dotenv
```

### 2. 환경 설정

환경변수 설정 파일(`.env`)을 생성하세요:

```bash
cp env.example .env
```

`.env` 파일을 편집하여 실제 환경에 맞게 설정을 수정하세요:

```env
# 시리얼 통신 설정
SERIAL_PORT=COM9                    # Windows: COM3, Linux: /dev/ttyUSB0
BAUD_RATE=9600

# DID 서버 설정 (바코드 데이터 전송용)
DID_SERVER=http://192.168.219.110
DID_PORT=5173

# BSD Syslog 서버 설정 (선택사항 - 로그 전송용)
BSD_SERVER=cloud.wlab.me
BSD_PORT=514

# 로깅 설정
ENABLE_ERROR_LOG_UPLOAD=True
LOG_DIRECTORY=logs
```

### 3. 환경변수 설명

| 환경변수 | 설명 | 기본값 | 예시 |
|---------|------|--------|------|
| `SERIAL_PORT` | 시리얼 포트 이름 | `COM9` | Windows: `COM3`, Linux: `/dev/ttyUSB0` |
| `BAUD_RATE` | 보드레이트 설정 | `9600` | `9600`, `115200` |
| `DID_SERVER` | DID 서버 주소 | `http://192.168.219.110` | `http://localhost`, `https://api.example.com` |
| `DID_PORT` | DID 서버 포트 | `5173` | `80`, `443`, `8080` |
| `BSD_SERVER` | Syslog 서버 주소 (선택) | `None` | `cloud.wlab.me`, `192.168.1.100` |
| `BSD_PORT` | Syslog 서버 포트 (선택) | `514` | `514`, `1514` |
| `ENABLE_ERROR_LOG_UPLOAD` | 에러 로그 서버 전송 | `True` | `True`, `False` |
| `LOG_DIRECTORY` | 로그 디렉토리 | `logs` | `logs`, `/var/log/barcode` |

### 4. 실행

```bash
python main.py
```

## 환경 요구사항

- **Python 3.6+**
- **Ubuntu/Linux** (GUI 없는 환경에 최적화)
- **시리얼 포트 접근 권한** (`sudo usermod -a -G dialout $USER`)

## 서버 API 요구사항

시스템이 정상 동작하려면 서버에 다음 엔드포인트가 구현되어야 합니다:

- **POST `/api/post`**: 바코드 데이터 수신
  ```json
  {"id": "barcode_value"}
  ```

- **POST `/api/health-log`**: 시스템 헬스 에러 로그 수신 (선택사항)
  ```json
  {
    "type": "health_error",
    "hostname": "server_hostname",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "errors": ["SERIAL_PORT_ERROR", "SERVER_CONNECTION_ERROR"],
    "status": {
      "serial_port": "ERROR",
      "server_connection": "ERROR", 
      "barcode_reader": "OK"
    }
  }
  ```

## 로컬 로그 파일 구조

시스템은 `logs/` 디렉토리에 날짜별로 로그 파일을 자동 생성합니다:

```
logs/
├── barcode_system_2024-01-15.log    # 전체 시스템 로그 (INFO, ERROR, DEBUG)
├── barcode_events_2024-01-15.log    # 바코드 전용 로그 (수신/전송/중복/실패)
├── errors_2024-01-15.log            # 에러 전용 로그
├── barcode_system_2024-01-14.log    # 이전 날짜 로그들...
└── ...
```

### 로그 파일 설명

- **전체 시스템 로그**: 모든 이벤트 (DEBUG 포함)
- **바코드 이벤트 로그**: 바코드 수신, 전송 성공/실패, 중복 검출
- **에러 로그**: 시스템 오류, 통신 실패, 헬스체크 실패

### 로그 예시

```
# barcode_events_2024-01-15.log
2024-01-15 10:30:15 [INFO]: BARCODE_RECEIVED: ABC123456
2024-01-15 10:30:15 [INFO]: BARCODE_SENT_SUCCESS: ABC123456
2024-01-15 10:30:20 [INFO]: DUPLICATE_BARCODE: ABC123456
2024-01-15 10:30:25 [ERROR]: BARCODE_SENT_FAILED: XYZ789 - HTTP 500: Internal Server Error
```

## 주요 기능

1. **바코드 읽기**: 시리얼 포트를 통한 바코드 데이터 수신
2. **중복 필터링**: 동일한 바코드 연속 전송 방지
3. **서버 전송**: 읽은 바코드를 REST API로 전송
4. **헬스체크**: 바코드 리더기 통신 상태 확인
5. **상태 모니터링**: 시리얼 포트, 서버, 바코드 리더 상태 주기적 확인 (5분마다)
6. **에러 로그 전송**: 시스템 헬스 에러를 서버로 자동 전송 (/api/health-log)
7. **로컬 파일 로깅**: 날짜별 상세 로그 파일 저장 (디버그 포함)
8. **바코드 추적**: 모든 바코드 이벤트 상세 추적 및 저장
9. **로그 로테이션**: 파일 크기 제한으로 디스크 공간 관리
10. **Syslog 지원**: 선택적 syslog 서버 연동 (NAS 등)

## 코드 구조의 장점

- **관심사 분리**: 각 모듈이 명확한 단일 책임을 가짐
- **재사용성**: 각 기능을 독립적으로 테스트 및 수정 가능
- **유지보수성**: 모듈별로 코드 관리가 용이
- **확장성**: 새로운 기능 추가 시 해당 모듈만 수정
- **테스트**: 각 모듈을 독립적으로 단위 테스트 가능 