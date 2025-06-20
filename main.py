"""
바코드 리더 시스템 메인 실행 파일
"""

import serial
import time

from config import SERIAL_PORT, BAUD_RATE, SERVER_HOST, CHECK_INTERVAL, HEALTH_CHECK_COMMANDS
from server_client import check_server_connection
from barcode_reader import (
    check_serial_port, read_barcode, open_serial_connection, 
    send_health_check_command, set_serial_connection,
    initialize_barcode_reader_times, get_barcode_reader_status
)
from monitor import start_status_monitor


def main():
    """
    메인 실행 함수
    """
    print("프로그램을 시작합니다.")
    print(f"시리얼 포트: {SERIAL_PORT}")
    print(f"서버 주소: {SERVER_HOST}")
    print(f"상태 체크 주기: {CHECK_INTERVAL}초 (5분)")
    print(f"헬스체크 명령어: {len(HEALTH_CHECK_COMMANDS)}개 명령어 지원")
    
    # 초기 시간 설정
    initialize_barcode_reader_times()
    
    # 상태 모니터링 스레드 시작
    start_status_monitor()
    
    # 초기 상태 체크
    if not check_serial_port():
        print(f"초기 시리얼 포트 연결 실패: {SERIAL_PORT}")
    
    check_server_connection()
    
    while True:
        try:
            # 시리얼 포트가 사용 가능한지 확인
            if not check_serial_port():
                print("시리얼 포트를 사용할 수 없습니다. 5초 후 재시도...")
                time.sleep(5)
                continue
                
            # 시리얼 포트 열기
            with serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1) as ser:
                set_serial_connection(ser)
                print(f"시리얼 포트 {SERIAL_PORT}을(를) {BAUD_RATE} 보드레이트로 열었습니다.")
                
                # 초기 헬스체크 수행
                print("초기 바코드 리더기 헬스체크 수행 중...")
                initial_health = send_health_check_command(ser)
                if initial_health:
                    print("초기 헬스체크 성공 - 바코드 리더기 통신 정상")
                else:
                    print("초기 헬스체크 실패 - 바코드 리더기 응답 없음")
                
                read_barcode(ser)
                
        except serial.SerialException as e:
            set_serial_connection(None)
            print(f"시리얼 포트 {SERIAL_PORT}을(를) 열 수 없습니다: {e}")
            print("5초 후 재시도...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"예상치 못한 오류: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main() 