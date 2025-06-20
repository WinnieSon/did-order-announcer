"""
시스템 헬스 에러 로그를 서버로 전송하고 로컬 파일에 저장하는 기능들
"""

import logging
import socket
import requests
import json
import os
from datetime import datetime
from logging.handlers import SysLogHandler, RotatingFileHandler

from config import SERVER_HOST, API_URL


class SystemLogger:
    """
    시스템 헬스 상태를 로깅하고 서버로 전송하며 로컬 파일에 저장하는 클래스
    """
    
    def __init__(self, syslog_address=None, log_dir="logs"):
        """
        시스템 로거 초기화
        
        Args:
            syslog_address (tuple): syslog 서버 주소 (host, port)
            log_dir (str): 로컬 로그 파일 저장 디렉토리
        """
        self.hostname = socket.gethostname()
        self.syslog_enabled = syslog_address is not None
        self.log_dir = log_dir
        
        # 로그 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 로거 설정
        self.logger = logging.getLogger('barcode-system')
        self.logger.setLevel(logging.DEBUG)  # 디버그 로그 포함
        
        # 기존 핸들러 제거 (중복 방지)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            f'%(asctime)s {self.hostname} %(name)s [%(levelname)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)  # 콘솔은 INFO 이상만
        self.logger.addHandler(console_handler)
        
        # 로컬 파일 핸들러 추가 (날짜별)
        self._setup_file_handlers()
        
        # syslog 핸들러 추가 (옵션)
        if self.syslog_enabled:
            try:
                syslog_handler = SysLogHandler(address=syslog_address, facility=SysLogHandler.LOG_USER)
                syslog_formatter = logging.Formatter(
                    f'%(asctime)s {self.hostname} %(name)s: %(message)s',
                    datefmt='%b %d %H:%M:%S'
                )
                syslog_handler.setFormatter(syslog_formatter)
                self.logger.addHandler(syslog_handler)
                self.log_info(f"Syslog 연결 성공: {syslog_address[0]}:{syslog_address[1]}")
            except Exception as e:
                self.log_error("Syslog", f"연결 실패: {e}")
                self.syslog_enabled = False
    
    def _setup_file_handlers(self):
        """
        날짜별 로컬 파일 핸들러를 설정합니다.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 전체 로그 파일 (모든 레벨)
        main_log_file = os.path.join(self.log_dir, f'barcode_system_{today}.log')
        main_file_handler = RotatingFileHandler(
            main_log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        main_file_formatter = logging.Formatter(
            f'%(asctime)s {self.hostname} %(name)s [%(levelname)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        main_file_handler.setFormatter(main_file_formatter)
        main_file_handler.setLevel(logging.DEBUG)  # 모든 로그 저장
        self.logger.addHandler(main_file_handler)
        
        # 바코드 전용 로그 파일
        barcode_log_file = os.path.join(self.log_dir, f'barcode_events_{today}.log')
        self.barcode_file_handler = RotatingFileHandler(
            barcode_log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        barcode_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.barcode_file_handler.setFormatter(barcode_formatter)
        
        # 에러 전용 로그 파일
        error_log_file = os.path.join(self.log_dir, f'errors_{today}.log')
        error_file_handler = RotatingFileHandler(
            error_log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        error_file_handler.setFormatter(main_file_formatter)
        error_file_handler.setLevel(logging.ERROR)  # 에러만 저장
        self.logger.addHandler(error_file_handler)
    
    def log_info(self, message):
        """정보 메시지를 로깅합니다."""
        self.logger.info(message)
    
    def log_success(self, message):
        """성공 메시지를 로깅합니다."""
        self.logger.info(f"✅ {message}")
    
    def log_error(self, error_type, error_message):
        """에러 메시지를 로깅합니다."""
        self.logger.error(f"❌ {error_type}: {error_message}")
    
    def log_warning(self, title, message):
        """경고 메시지를 로깅합니다."""
        self.logger.warning(f"⚠️  {title}: {message}")
    
    def log_debug(self, message):
        """디버그 메시지를 로깅합니다."""
        self.logger.debug(f"🔍 {message}")
    
    def log_barcode_received(self, barcode, is_duplicate=False):
        """
        바코드 수신 이벤트를 로깅합니다.
        
        Args:
            barcode (str): 바코드 데이터
            is_duplicate (bool): 중복 바코드 여부
        """
        if is_duplicate:
            message = f"DUPLICATE_BARCODE: {barcode}"
            self.logger.info(message)
        else:
            message = f"BARCODE_RECEIVED: {barcode}"
            self.logger.info(message)
        
        # 바코드 전용 파일에도 기록
        barcode_logger = logging.getLogger('barcode-events')
        if not barcode_logger.handlers:
            barcode_logger.addHandler(self.barcode_file_handler)
            barcode_logger.setLevel(logging.INFO)
        barcode_logger.info(message)
    
    def log_barcode_send_result(self, barcode, success, error_msg=None):
        """
        바코드 서버 전송 결과를 로깅합니다.
        
        Args:
            barcode (str): 바코드 데이터
            success (bool): 전송 성공 여부
            error_msg (str): 실패 시 에러 메시지
        """
        if success:
            message = f"BARCODE_SENT_SUCCESS: {barcode}"
            self.logger.info(message)
        else:
            message = f"BARCODE_SENT_FAILED: {barcode} - {error_msg}"
            self.logger.error(message)
        
        # 바코드 전용 파일에도 기록
        barcode_logger = logging.getLogger('barcode-events')
        if not barcode_logger.handlers:
            barcode_logger.addHandler(self.barcode_file_handler)
            barcode_logger.setLevel(logging.INFO)
        
        if success:
            barcode_logger.info(message)
        else:
            barcode_logger.error(message)
    
    def log_system_health(self, serial_status, server_status, barcode_reader_status):
        """
        시스템 헬스 상태를 로깅합니다.
        
        Args:
            serial_status (bool): 시리얼 포트 상태
            server_status (bool): 서버 연결 상태
            barcode_reader_status (bool): 바코드 리더 상태
        """
        timestamp = datetime.now().isoformat()
        
        # 시스템 헬스 상태 정보
        health_data = {
            'timestamp': timestamp,
            'hostname': self.hostname,
            'serial_port': 'OK' if serial_status else 'ERROR',
            'server_connection': 'OK' if server_status else 'ERROR',
            'barcode_reader': 'OK' if barcode_reader_status else 'INACTIVE'
        }
        
        # 에러 상태 확인
        errors = []
        if not serial_status:
            errors.append('SERIAL_PORT_ERROR')
        if not server_status:
            errors.append('SERVER_CONNECTION_ERROR')
        if not barcode_reader_status:
            errors.append('BARCODE_READER_INACTIVE')
        
        if errors:
            # 에러가 있으면 에러 로그 전송
            error_message = f"System health errors detected: {', '.join(errors)}"
            self.logger.error(error_message)
            self._send_error_to_server(health_data, errors)
        else:
            # 모든 상태가 정상이면 정보 로그
            success_message = "System health check: All systems OK"
            self.logger.info(success_message)
    
    def _send_error_to_server(self, health_data, errors):
        """
        에러 로그를 REST API로 서버에 전송합니다.
        
        Args:
            health_data (dict): 시스템 헬스 데이터
            errors (list): 에러 목록
        """
        try:
            # 에러 로그 API 엔드포인트 (기본 API_URL 기반)
            log_api_url = API_URL.replace('/api/post', '/api/health-log')
            
            log_payload = {
                'type': 'health_error',
                'hostname': self.hostname,
                'timestamp': health_data['timestamp'],
                'errors': errors,
                'status': {
                    'serial_port': health_data['serial_port'],
                    'server_connection': health_data['server_connection'],
                    'barcode_reader': health_data['barcode_reader']
                }
            }
            
            response = requests.post(log_api_url, json=log_payload, timeout=10)
            if response.status_code == 200:
                self.log_success(f"헬스 에러 로그 서버 전송 성공: {len(errors)}개 에러")
            else:
                self.log_error("로그 전송", f"헬스 에러 로그 전송 실패. 상태 코드: {response.status_code}")
                
        except Exception as e:
            self.log_error("로그 전송", f"헬스 에러 로그 서버 전송 오류: {e}")
    
    def log_barcode_event(self, barcode, status):
        """
        바코드 이벤트를 로깅합니다.
        
        Args:
            barcode (str): 바코드 데이터
            status (str): 전송 상태 ('success' 또는 'failed')
        """
        timestamp = datetime.now().isoformat()
        message = f"Barcode {status}: {barcode} at {timestamp}"
        
        if status == 'success':
            self.logger.info(message)
        else:
            self.logger.error(message)
    
    def log_custom_error(self, error_type, error_message):
        """
        사용자 정의 에러를 로깅합니다.
        
        Args:
            error_type (str): 에러 타입
            error_message (str): 에러 메시지
        """
        message = f"{error_type}: {error_message}"
        self.logger.error(message)


# 전역 로거 인스턴스
system_logger = None


def initialize_logger(syslog_address=None, log_dir="logs"):
    """
    시스템 로거를 초기화합니다.
    
    Args:
        syslog_address (tuple): syslog 서버 주소 (선택사항)
        log_dir (str): 로컬 로그 디렉토리
    """
    global system_logger
    system_logger = SystemLogger(syslog_address, log_dir)
    return system_logger


def get_logger():
    """
    현재 시스템 로거 인스턴스를 반환합니다.
    
    Returns:
        SystemLogger: 로거 인스턴스
    """
    global system_logger
    if system_logger is None:
        system_logger = SystemLogger()
    return system_logger


# UI Utils 대체 함수들
def log_info(message):
    """정보 메시지를 로깅합니다."""
    logger = get_logger()
    logger.log_info(message)


def log_success(message):
    """성공 메시지를 로깅합니다."""
    logger = get_logger()
    logger.log_success(message)


def log_error(error_type, error_message):
    """에러 메시지를 로깅합니다."""
    logger = get_logger()
    logger.log_error(error_type, error_message)


def show_warning_message(title, message):
    """경고 메시지를 로깅합니다."""
    logger = get_logger()
    logger.log_warning(title, message)


def log_debug(message):
    """디버그 메시지를 로깅합니다."""
    logger = get_logger()
    logger.log_debug(message) 