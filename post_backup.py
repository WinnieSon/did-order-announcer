import serial
import requests
import time
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
 
# 설정
SERIAL_PORT = 'COM9'        # 시리얼 포트 이름 (예: 'COM3' for Windows, '/dev/ttyUSB0' for Linux)
BAUD_RATE = 9600            # 보드레이트 설정
API_URL = 'http://192.168.219.110:5173/api/post'  # API 엔드포인트
SERVER_HOST = 'http://192.168.219.110:5173'  # 서버 호스트 (핑 체크용)
CHECK_INTERVAL = 300  # 5분 (300초)

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

# 상태 변수들
last_sent_barcode = None
serial_connection = None
last_barcode_time = None
last_health_check_time = None
serial_port_available = False
barcode_reader_active = False
server_available = False

# 마지막 경고 시간 추적
last_serial_warning = None
last_barcode_warning = None  
last_server_warning = None

def show_warning_message(title, message):
    """
    경고 메시지를 표시합니다.
    """
    try:
        # 메인 윈도우 없이 메시지박스만 표시
        root = tk.Tk()
        root.withdraw()  # 메인 윈도우 숨기기
        messagebox.showwarning(title, message)
        root.destroy()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 경고: {message}")
    except Exception as e:
        print(f"메시지박스 표시 오류: {e}")

def check_serial_port():
    """
    시리얼 포트 연결 상태를 확인합니다.
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
            current_time - last_serial_warning >= timedelta(minutes=5)):
            show_warning_message(
                "시리얼 포트 연결 오류",
                f"시리얼 포트 {SERIAL_PORT}에 연결할 수 없습니다.\n바코드 리더가 제대로 연결되어 있는지 확인해주세요."
            )
            last_serial_warning = current_time
        
        return False

def check_server_connection():
    """
    서버 연결 상태를 확인합니다.
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
            current_time - last_server_warning >= timedelta(minutes=5)):
            show_warning_message(
                "서버 연결 오류", 
                f"서버 {SERVER_HOST}에 연결할 수 없습니다.\n네트워크 연결 상태를 확인해주세요."
            )
            last_server_warning = current_time
        
        return False

def send_health_check_command(serial_conn):
    """
    바코드 리더기에 헬스체크 명령어를 전송하고 응답을 확인합니다.
    """
    for i, command in enumerate(HEALTH_CHECK_COMMANDS):
        try:
            print(f"헬스체크 명령 {i+1}/{len(HEALTH_CHECK_COMMANDS)} 전송 중...")
            
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
                    print(f"헬스체크 응답 받음: {response}")
                    
                    # 응답이 유효한지 확인
                    if any(valid_resp in response for valid_resp in VALID_RESPONSES):
                        print(f"바코드 리더기 헬스체크 성공 (명령어 {i+1})")
                        return True
                    elif len(response) > 0:
                        print(f"알 수 없는 응답: {response}")
                        return True  # 어떤 응답이라도 받았으면 통신은 됨
                
                time.sleep(0.1)
                
        except Exception as e:
            print(f"헬스체크 명령어 {i+1} 전송 오류: {e}")
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
         current_time - last_health_check_time >= timedelta(minutes=2))):  # 2분마다 헬스체크
        
        print("바코드 리더기 헬스체크 실행 중...")
        health_check_success = send_health_check_command(serial_connection)
        last_health_check_time = current_time
        
        if health_check_success:
            barcode_reader_active = True
            print("바코드 리더기 헬스체크 성공 - 통신 정상")
        else:
            barcode_reader_active = False
            
            # 5분마다 또는 처음 실행시에만 경고 메시지 표시
            if (last_barcode_warning is None or 
                current_time - last_barcode_warning >= timedelta(minutes=5)):
                show_warning_message(
                    "바코드 리더 통신 오류",
                    "바코드 리더기와의 통신이 원활하지 않습니다.\n헬스체크 명령에 응답하지 않습니다.\n리더기 상태를 확인해주세요."
                )
                last_barcode_warning = current_time
    
    # 시리얼 포트가 열려있지 않으면 비활성 상태
    elif not serial_port_available or not serial_connection:
        barcode_reader_active = False

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
            status_msg += f"시리얼포트: {'OK' if serial_port_available else 'ERROR'}, "
            status_msg += f"서버: {'OK' if server_available else 'ERROR'}, "
            status_msg += f"바코드리더: {'OK' if barcode_reader_active else 'INACTIVE'}"
            print(status_msg)
            
        except Exception as e:
            print(f"상태 모니터링 오류: {e}")
        
        time.sleep(CHECK_INTERVAL)  # 5분 대기

def read_barcode(serial_conn):
    """
    시리얼 포트로부터 바코드 데이터를 읽어 서버로 전송합니다.
    중복된 바코드는 전송하지 않습니다.
    """
    global last_sent_barcode, last_barcode_time, barcode_reader_active
    
    while True:
        try:
            # 시리얼 포트에서 한 줄 읽기
            line = serial_conn.readline().decode('utf-8').strip()
            if line:
                # 헬스체크 응답인지 확인 (바코드 데이터와 구분)
                if any(valid_resp.decode('utf-8', errors='ignore') in line for valid_resp in VALID_RESPONSES):
                    print(f"헬스체크 응답 수신: {line}")
                    continue
                
                # 바코드 데이터를 받았으므로 시간 업데이트
                last_barcode_time = datetime.now()
                barcode_reader_active = True
                
                # 여러 바코드가 포함될 수 있으므로 분리
                # \n 또는 공백을 기준으로 분리
                barcodes = line.replace('\n', ' ').split()
                for barcode in barcodes:
                    if barcode != last_sent_barcode:
                        print(f"받은 바코드: {barcode}")
                        send_to_server(barcode)
                        last_sent_barcode = barcode
                    else:
                        print(f"중복된 바코드 {barcode}는 전송하지 않습니다.")
        except Exception as e:
            print(f"시리얼 포트 읽기 오류: {e}")
            time.sleep(1)  # 오류 발생 시 잠시 대기
 
def send_to_server(barcode):
    """
    읽은 바코드를 서버에 POST 요청으로 전송합니다.
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
 
def main():
    global serial_connection, last_barcode_time, last_health_check_time
    
    print("프로그램을 시작합니다.")
    print(f"시리얼 포트: {SERIAL_PORT}")
    print(f"서버 주소: {SERVER_HOST}")
    print(f"상태 체크 주기: {CHECK_INTERVAL}초 (5분)")
    print(f"헬스체크 명령어: {len(HEALTH_CHECK_COMMANDS)}개 명령어 지원")
    
    # 초기 시간 설정
    current_time = datetime.now()
    last_barcode_time = current_time
    last_health_check_time = current_time
    
    # 상태 모니터링 스레드 시작
    monitor_thread = threading.Thread(target=status_monitor, daemon=True)
    monitor_thread.start()
    print("상태 모니터링 시작됨")
    
    # 초기 상태 체크
    if not check_serial_port():
        print(f"초기 시리얼 포트 연결 실패: {SERIAL_PORT}")
    
    check_server_connection()
    
    while True:
        try:
            # 시리얼 포트가 사용 가능한지 확인
            if not serial_port_available:
                print("시리얼 포트를 사용할 수 없습니다. 5초 후 재시도...")
                time.sleep(5)
                continue
                
            # 시리얼 포트 열기
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                serial_connection = ser
                print(f"시리얼 포트 {SERIAL_PORT}을(를) {BAUD_RATE} 보드레이트로 열었습니다.")
                
                # 초기 헬스체크 수행
                print("초기 바코드 리더기 헬스체크 수행 중...")
                initial_health = send_health_check_command(ser)
                if initial_health:
                    print("초기 헬스체크 성공 - 바코드 리더기 통신 정상")
                    barcode_reader_active = True
                else:
                    print("초기 헬스체크 실패 - 바코드 리더기 응답 없음")
                    barcode_reader_active = False
                
                read_barcode(ser)
                
        except serial.SerialException as e:
            serial_connection = None
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
