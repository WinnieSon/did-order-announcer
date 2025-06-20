"""
바코드 리더 시스템 설정 파일
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 시리얼 통신 설정
SERIAL_PORT = os.getenv('SERIAL_PORT', 'COM9')      # 시리얼 포트 이름 (예: 'COM3' for Windows, '/dev/ttyUSB0' for Linux)
BAUD_RATE = int(os.getenv('BAUD_RATE', '9600'))     # 보드레이트 설정

# 서버 설정
DID_SERVER = os.getenv('DID_SERVER', 'http://192.168.219.110')
DID_PORT = int(os.getenv('DID_PORT', '5173'))
API_URL = f'{DID_SERVER}:{DID_PORT}/api/post'       # API 엔드포인트
SERVER_HOST = f'{DID_SERVER}:{DID_PORT}'            # 서버 호스트 (핑 체크용)

# 모니터링 설정
CHECK_INTERVAL = 300        # 5분 (300초) - 상태 체크 주기
HEALTH_CHECK_INTERVAL = 120 # 2분 (120초) - 헬스체크 주기
WARNING_INTERVAL = 300      # 5분 (300초) - 경고 메시지 표시 간격

# 로깅 설정
BSD_SERVER = os.getenv('BSD_SERVER')
BSD_PORT = int(os.getenv('BSD_PORT', '514')) if os.getenv('BSD_PORT') else None
SYSLOG_ADDRESS = (BSD_SERVER, BSD_PORT) if BSD_SERVER and BSD_PORT else None  # syslog 서버 주소
ENABLE_ERROR_LOG_UPLOAD = os.getenv('ENABLE_ERROR_LOG_UPLOAD', 'True').lower() == 'true'  # 에러 로그 서버 전송 활성화
LOG_DIRECTORY = os.getenv('LOG_DIRECTORY', 'logs')  # 로컬 로그 파일 저장 디렉토리

# 바코드 리더기 헬스체크 명령어들 (표준 프로토콜)
HEALTH_CHECK_COMMANDS = [
    b'\x05',                    # ENQ (Enquiry) - 기본 통신 확인
    b'\x02STATUS\x03',          # STATUS 명령어 (STX + STATUS + ETX)
    b'\x02VER\x03',             # VERSION 조회
    b'\x02BEEP\x03',            # BEEP 명령어 - 물리적 응답 확인
    b'STATUS\r\n',              # 일부 리더기용 STATUS 명령
    b'?\r\n',                   # 간단한 응답 확인
]

# 예상되는 응답 패턴들
VALID_RESPONSES = [
    b'\x06',                    # ACK (Acknowledge)
    b'\x15',                    # NAK (Negative Acknowledge)
    b'OK',                      # OK 응답
    b'STATUS',                  # STATUS 응답
    b'VER',                     # VERSION 응답
    b'BEEP',                    # BEEP 응답
    b'READY',                   # READY 응답
] 