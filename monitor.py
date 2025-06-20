"""
시스템 상태 모니터링 관련 기능들
"""

import time
import threading
from datetime import datetime

from config import CHECK_INTERVAL, SYSLOG_ADDRESS, ENABLE_ERROR_LOG_UPLOAD, LOG_DIRECTORY
from server_client import check_server_connection, get_server_status
from barcode_reader import check_serial_port, check_barcode_reader_activity, get_serial_status, get_barcode_reader_status
from logging_client import initialize_logger, get_logger
from logging_client import log_info, log_error


def status_monitor():
    """
    5분마다 시스템 상태를 확인하고 에러 시 서버로 로그를 전송합니다.
    """
    while True:
        try:
            # 시스템 상태 체크
            check_serial_port()
            check_server_connection() 
            check_barcode_reader_activity()
            
            # 현재 상태 가져오기
            serial_status = get_serial_status()
            server_status = get_server_status()
            barcode_reader_status = get_barcode_reader_status()
            
            # 상태 로그 출력
            status_msg = f"상태 체크 - "
            status_msg += f"시리얼포트: {'OK' if serial_status else 'ERROR'}, "
            status_msg += f"서버: {'OK' if server_status else 'ERROR'}, "
            status_msg += f"바코드리더: {'OK' if barcode_reader_status else 'INACTIVE'}"
            
            if serial_status and server_status and barcode_reader_status:
                log_info(status_msg)
            else:
                log_error("시스템 상태 체크", status_msg)
            
            # 에러 로그 서버 전송 (설정이 활성화된 경우)
            if ENABLE_ERROR_LOG_UPLOAD:
                logger = get_logger()
                logger.log_system_health(serial_status, server_status, barcode_reader_status)
            
        except Exception as e:
            error_msg = f"상태 모니터링 오류: {e}"
            log_error("모니터링", error_msg)
            
            # 모니터링 자체 오류도 서버로 전송
            if ENABLE_ERROR_LOG_UPLOAD:
                try:
                    logger = get_logger()
                    logger.log_custom_error("MONITORING_ERROR", str(e))
                except Exception as log_e:
                    print(f"로그 전송 오류: {log_e}")
        
        time.sleep(CHECK_INTERVAL)  # 5분 대기


def start_status_monitor():
    """
    상태 모니터링을 백그라운드 스레드로 시작합니다.
    
    Returns:
        threading.Thread: 모니터링 스레드 객체
    """
    # 로거 초기화
    if ENABLE_ERROR_LOG_UPLOAD:
        initialize_logger(SYSLOG_ADDRESS, LOG_DIRECTORY)
        log_info(f"시스템 로거 초기화 완료 (로그 디렉토리: {LOG_DIRECTORY})")
    else:
        # 에러 로그 업로드가 비활성화되어도 로컬 로깅은 활성화
        initialize_logger(None, LOG_DIRECTORY)
        log_info(f"로컬 로거 초기화 완료 (로그 디렉토리: {LOG_DIRECTORY})")
    
    monitor_thread = threading.Thread(target=status_monitor, daemon=True)
    monitor_thread.start()
    log_info("상태 모니터링 시작됨")
    return monitor_thread 