"""
바코드 리더 관련 기능들 (시리얼 통신, 헬스체크)
"""

import serial
import time
from datetime import datetime, timedelta

from config import (
    SERIAL_PORT, BAUD_RATE, HEALTH_CHECK_COMMANDS, VALID_RESPONSES,
    WARNING_INTERVAL, HEALTH_CHECK_INTERVAL
)
from logging_client import show_warning_message, log_info, log_error, log_success, log_debug
from server_client import send_to_server


# 상태 변수들
serial_port_available = False
barcode_reader_active = False
serial_connection = None
last_barcode_time = None
last_health_check_time = None
last_sent_barcode = None
last_serial_warning = None
last_barcode_warning = None


def check_serial_port():
    """
    시리얼 포트 연결 상태를 확인합니다.
    
    Returns:
        bool: 시리얼 포트 연결 가능 여부
    """
    global serial_port_available, last_serial_warning
    
    try:
        test_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        test_serial.close()
        serial_port_available = True
        return True
    except serial.SerialException:
        serial_port_available = False
        current_time = datetime.now()
        
        # 5분마다 또는 처음 실행시에만 경고 메시지 표시
        if (last_serial_warning is None or 
            current_time - last_serial_warning >= timedelta(seconds=WARNING_INTERVAL)):
            show_warning_message(
                "시리얼 포트 연결 오류",
                f"시리얼 포트 {SERIAL_PORT}에 연결할 수 없습니다.\n바코드 리더가 제대로 연결되어 있는지 확인해주세요."
            )
            last_serial_warning = current_time
        
        return False


def send_health_check_command(serial_conn):
    """
    바코드 리더기에 헬스체크 명령어를 전송하고 응답을 확인합니다.
    
    Args:
        serial_conn: 시리얼 연결 객체
        
    Returns:
        bool: 헬스체크 성공 여부
    """
    for i, command in enumerate(HEALTH_CHECK_COMMANDS):
        try:
            log_debug(f"헬스체크 명령 {i+1}/{len(HEALTH_CHECK_COMMANDS)} 전송 중: {command}")
            
            # 버퍼 비우기
            serial_conn.reset_input_buffer()
            serial_conn.reset_output_buffer()
            
            # 명령어 전송
            serial_conn.write(command)
            time.sleep(0.1)  # 리더기 응답 대기
            
            # 응답 확인 (여러 번 시도)
            for attempt in range(3):
                if serial_conn.in_waiting > 0:
                    response = serial_conn.read(serial_conn.in_waiting)
                    log_debug(f"헬스체크 응답 받음 (시도 {attempt+1}): {response}")
                    
                    # 응답이 유효한지 확인
                    if any(valid_resp in response for valid_resp in VALID_RESPONSES):
                        log_success(f"바코드 리더기 헬스체크 성공 (명령어 {i+1})")
                        return True
                    elif len(response) > 0:
                        log_debug(f"알 수 없는 응답이지만 통신 확인됨: {response}")
                        return True  # 어떤 응답이라도 받았으면 통신은 됨
                else:
                    log_debug(f"헬스체크 응답 대기 중 (시도 {attempt+1}/3)")
                
                time.sleep(0.1)
                
        except Exception as e:
            log_error("헬스체크", f"명령어 {i+1} 전송 오류: {e}")
            continue
    
    return False


def check_barcode_reader_activity():
    """
    바코드 리더 활동 상태를 확인합니다.
    """
    global barcode_reader_active, last_barcode_warning, last_barcode_time, last_health_check_time
    
    current_time = datetime.now()
    
    # 바코드 데이터를 최근에 받았으면 활성 상태로 간주
    if last_barcode_time and current_time - last_barcode_time < timedelta(minutes=5):
        barcode_reader_active = True
        return
    
    # 바코드 데이터를 받지 못했으면 헬스체크로 통신 상태 확인
    if (serial_port_available and serial_connection and 
        (last_health_check_time is None or 
         current_time - last_health_check_time >= timedelta(seconds=HEALTH_CHECK_INTERVAL))):
        
        print("바코드 리더기 헬스체크 실행 중...")
        health_check_success = send_health_check_command(serial_connection)
        last_health_check_time = current_time
        
        if health_check_success:
            barcode_reader_active = True
            log_success("바코드 리더기 헬스체크 성공 - 통신 정상")
        else:
            barcode_reader_active = False
            
            # 5분마다 또는 처음 실행시에만 경고 메시지 표시
            if (last_barcode_warning is None or 
                current_time - last_barcode_warning >= timedelta(seconds=WARNING_INTERVAL)):
                show_warning_message(
                    "바코드 리더 통신 오류",
                    "바코드 리더기와의 통신이 원활하지 않습니다.\n헬스체크 명령에 응답하지 않습니다.\n리더기 상태를 확인해주세요."
                )
                last_barcode_warning = current_time
    
    # 시리얼 포트가 열려있지 않으면 비활성 상태
    elif not serial_port_available or not serial_connection:
        barcode_reader_active = False


def read_barcode(serial_conn):
    """
    시리얼 포트로부터 바코드 데이터를 읽어 서버로 전송합니다.
    중복된 바코드는 전송하지 않습니다.
    
    Args:
        serial_conn: 시리얼 연결 객체
    """
    global last_sent_barcode, last_barcode_time, barcode_reader_active
    
    while True:
        try:
            # 시리얼 포트에서 한 줄 읽기
            line = serial_conn.readline().decode('utf-8').strip()
            if line:
                log_debug(f"시리얼 포트에서 데이터 수신: '{line}' (길이: {len(line)})")
                
                # 헬스체크 응답인지 확인 (바코드 데이터와 구분)
                if any(valid_resp.decode('utf-8', errors='ignore') in line for valid_resp in VALID_RESPONSES):
                    log_debug(f"헬스체크 응답으로 분류된 데이터: {line}")
                    continue
                
                # 바코드 데이터를 받았으므로 시간 업데이트
                last_barcode_time = datetime.now()
                barcode_reader_active = True
                
                # 여러 바코드가 포함될 수 있으므로 분리
                # \n 또는 공백을 기준으로 분리
                barcodes = line.replace('\n', ' ').split()
                for barcode in barcodes:
                    if barcode != last_sent_barcode:
                        log_info(f"받은 바코드: {barcode}")
                        log_debug(f"바코드 데이터 길이: {len(barcode)}, 내용: '{barcode}'")
                        
                        # 바코드 수신 이벤트 로깅
                        try:
                            from logging_client import get_logger
                            logger = get_logger()
                            logger.log_barcode_received(barcode, is_duplicate=False)
                        except Exception:
                            pass  # 로깅 실패는 무시
                        
                        send_to_server(barcode)
                        last_sent_barcode = barcode
                    else:
                        log_info(f"중복된 바코드 {barcode}는 전송하지 않습니다.")
                        log_debug(f"중복 바코드 상세: 이전='{last_sent_barcode}', 현재='{barcode}'")
                        
                        # 중복 바코드 이벤트 로깅
                        try:
                            from logging_client import get_logger
                            logger = get_logger()
                            logger.log_barcode_received(barcode, is_duplicate=True)
                        except Exception:
                            pass  # 로깅 실패는 무시
        except Exception as e:
            log_error("시리얼 포트", f"읽기 오류: {e}")
            time.sleep(1)  # 오류 발생 시 잠시 대기


def open_serial_connection():
    """
    시리얼 연결을 열고 관리합니다.
    
    Returns:
        serial.Serial or None: 성공시 시리얼 객체, 실패시 None
    """
    global serial_connection
    
    try:
        serial_connection = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        log_success(f"시리얼 포트 {SERIAL_PORT}을(를) {BAUD_RATE} 보드레이트로 열었습니다.")
        return serial_connection
    except serial.SerialException as e:
        serial_connection = None
        log_error("시리얼 포트", f"{SERIAL_PORT}을(를) 열 수 없습니다: {e}")
        return None


def get_serial_status():
    """
    시리얼 포트 연결 상태를 반환합니다.
    
    Returns:
        bool: 시리얼 포트 연결 상태
    """
    return serial_port_available


def get_barcode_reader_status():
    """
    바코드 리더 활성 상태를 반환합니다.
    
    Returns:
        bool: 바코드 리더 활성 상태
    """
    return barcode_reader_active


def set_serial_connection(connection):
    """
    시리얼 연결 객체를 설정합니다.
    
    Args:
        connection: 시리얼 연결 객체
    """
    global serial_connection
    serial_connection = connection


def initialize_barcode_reader_times():
    """
    바코드 리더 관련 시간 변수들을 초기화합니다.
    """
    global last_barcode_time, last_health_check_time
    current_time = datetime.now()
    last_barcode_time = current_time
    last_health_check_time = current_time 