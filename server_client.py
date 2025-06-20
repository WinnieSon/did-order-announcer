"""
서버 통신 관련 기능들
"""

import requests
from datetime import datetime, timedelta

from config import API_URL, SERVER_HOST, WARNING_INTERVAL, ENABLE_ERROR_LOG_UPLOAD
from logging_client import show_warning_message, log_success, log_error


# 상태 변수들
server_available = False
last_server_warning = None


def check_server_connection():
    """
    서버 연결 상태를 확인합니다.
    
    Returns:
        bool: 서버 연결 가능 여부
    """
    global server_available, last_server_warning
    
    try:
        response = requests.get(SERVER_HOST, timeout=5)
        server_available = True
        return True
    except Exception:
        server_available = False
        current_time = datetime.now()
        
        # 5분마다 또는 처음 실행시에만 경고 메시지 표시
        if (last_server_warning is None or 
            current_time - last_server_warning >= timedelta(seconds=WARNING_INTERVAL)):
            show_warning_message(
                "서버 연결 오류", 
                f"서버 {SERVER_HOST}에 연결할 수 없습니다.\n네트워크 연결 상태를 확인해주세요."
            )
            last_server_warning = current_time
        
        return False


def send_to_server(barcode):
    """
    읽은 바코드를 서버에 POST 요청으로 전송합니다.
    
    Args:
        barcode (str): 전송할 바코드 데이터
    """
    payload = {'id': barcode}
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        if response.status_code == 200:
            log_success(f"바코드 {barcode} 서버 전송 성공")
            
            # 성공 로그를 시스템 로거에도 기록
            if ENABLE_ERROR_LOG_UPLOAD:
                try:
                    from logging_client import get_logger
                    logger = get_logger()
                    logger.log_barcode_send_result(barcode, True)
                    logger.log_barcode_event(barcode, 'success')
                except Exception:
                    pass  # 로깅 실패는 무시
        else:
            error_msg = f"바코드 {barcode} 전송 실패. 상태 코드: {response.status_code}, 응답: {response.text}"
            log_error("바코드 전송", error_msg)
            
            # 실패 로그를 시스템 로거에도 기록
            if ENABLE_ERROR_LOG_UPLOAD:
                try:
                    from logging_client import get_logger
                    logger = get_logger()
                    logger.log_barcode_send_result(barcode, False, f"HTTP {response.status_code}: {response.text}")
                    logger.log_barcode_event(barcode, 'failed')
                except Exception:
                    pass  # 로깅 실패는 무시
    except Exception as e:
        error_msg = f"서버 전송 오류: {e}"
        log_error("바코드 전송", error_msg)
        
        # 예외 로그를 시스템 로거에도 기록
        if ENABLE_ERROR_LOG_UPLOAD:
            try:
                from logging_client import get_logger
                logger = get_logger()
                logger.log_barcode_send_result(barcode, False, str(e))
                logger.log_custom_error("BARCODE_SEND_ERROR", f"{barcode}: {str(e)}")
            except Exception:
                pass  # 로깅 실패는 무시


def get_server_status():
    """
    서버 연결 상태를 반환합니다.
    
    Returns:
        bool: 서버 연결 상태
    """
    return server_available 