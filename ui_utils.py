"""
UI 관련 유틸리티 함수들
"""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime


def show_warning_message(title, message):
    """
    경고 메시지를 표시합니다.
    
    Args:
        title (str): 경고 창 제목
        message (str): 경고 메시지 내용
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