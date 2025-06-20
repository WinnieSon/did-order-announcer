import logging
import socket
from logging.handlers import SysLogHandler

# NAS 주소와 포트
SYSLOG_ADDRESS = ('cloud.wlab.me', 514)

# 1) 로거 생성 및 레벨 설정
logger = logging.getLogger('test-logger')
logger.setLevel(logging.INFO)

# 2) SysLogHandler 설정 (UDP)
handler = SysLogHandler(address=SYSLOG_ADDRESS, facility=SysLogHandler.LOG_USER)
# hostname() 호출 지연 문제를 피하기 위해 직접 가져와서 포맷에 넣습니다.
hostname = socket.gethostname()
formatter = logging.Formatter(f'%(asctime)s {hostname} %(name)s: %(message)s',
                              datefmt='%b %d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# 3) 테스트 메시지 전송
if __name__ == '__main__':
    logger.info('Hello from Python to BSD syslog!')
    print(f"Sent test syslog to {SYSLOG_ADDRESS[0]}:{SYSLOG_ADDRESS[1]}")
