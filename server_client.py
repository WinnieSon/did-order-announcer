"""
서버 통신 관련 기능들
"""

import requests
from datetime import datetime, timedelta

from config import API_URL, SERVER_HOST, WARNING_INTERVAL
from ui_utils import show_warning_message


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
            print(f"바코드 {barcode} 서버 전송 성공.")
        else:
            print(f"바코드 {barcode} 전송 실패. 상태 코드: {response.status_code}, 응답: {response.text}")
    except Exception as e:
        print(f"서버 전송 오류: {e}")


def get_server_status():
    """
    서버 연결 상태를 반환합니다.
    
    Returns:
        bool: 서버 연결 상태
    """
    return server_available 