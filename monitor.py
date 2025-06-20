"""
시스템 상태 모니터링 관련 기능들
"""

import time
import threading
from datetime import datetime

from config import CHECK_INTERVAL
from server_client import check_server_connection, get_server_status
from barcode_reader import check_serial_port, check_barcode_reader_activity, get_serial_status, get_barcode_reader_status


def status_monitor():
    """
    5분마다 시스템 상태를 확인합니다.
    """
    while True:
        try:
            check_serial_port()
            check_server_connection() 
            check_barcode_reader_activity()
            
            # 상태 로그 출력
            status_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 상태 체크 - "
            status_msg += f"시리얼포트: {'OK' if get_serial_status() else 'ERROR'}, "
            status_msg += f"서버: {'OK' if get_server_status() else 'ERROR'}, "
            status_msg += f"바코드리더: {'OK' if get_barcode_reader_status() else 'INACTIVE'}"
            print(status_msg)
            
        except Exception as e:
            print(f"상태 모니터링 오류: {e}")
        
        time.sleep(CHECK_INTERVAL)  # 5분 대기


def start_status_monitor():
    """
    상태 모니터링을 백그라운드 스레드로 시작합니다.
    
    Returns:
        threading.Thread: 모니터링 스레드 객체
    """
    monitor_thread = threading.Thread(target=status_monitor, daemon=True)
    monitor_thread.start()
    print("상태 모니터링 시작됨")
    return monitor_thread 