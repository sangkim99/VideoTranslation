import cv2
import grpc
import numpy as np
import mediapipe as mp
import sys
import os
import time

# gen 폴더를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'gen'))

# proto 파일 import
from gen import middleware_pb2
from gen import middleware_pb2_grpc
from gen import error_pb2

def test_frame_to_marking_data(video_path):
    # gRPC 채널 설정
    channel = grpc.insecure_channel(
        '13.125.250.244:8088',
        options=[
            ('grpc.max_send_message_length', 10 * 1024 * 1024),
            ('grpc.max_receive_message_length', 10 * 1024 * 1024)
        ]
    )
    stub = middleware_pb2_grpc.ChangeMiddlwareStub(channel)

    # 비디오 열기
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ 비디오를 열 수 없습니다.")
        return

    # 비디오 FPS 설정 (30fps)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # 프레임 스트림 생성
    def frame_iterator():
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 프레임을 바이트로 변환
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()


            # gRPC 요청 생성
            request = middleware_pb2.FrameToMarkingDataRequest(
                frame=[frame_bytes],
                store_id="Y7JY8M5v",
                inquiry_type="inquiry",
                num=1
            )
            yield request

            # 30fps에 맞춰 대기
            time.sleep(1/30)

    # gRPC 요청 전송 (하나의 스트림으로)
    try:
        response = stub.FrameToMarkingData(frame_iterator())
        if response.error:
            error_name = error_pb2.EError.Name(response.error)
            print(f"응답: success={response.success}, error={error_name}")
        else:
            print(f"응답: success={response.success}")
    except Exception as e:
        print(f"에러 발생: {e}")
        if hasattr(e, 'details'):
            print(f"상세 에러: {e.details()}")

    cap.release()

if __name__ == "__main__":
    video_path = "긍긍정.mp4"
    test_frame_to_marking_data(video_path)