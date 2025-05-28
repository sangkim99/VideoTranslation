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
from google.protobuf.json_format import MessageToJson

def test_frame_to_marking_data(video_path):
    # gRPC 채널 설정
    channel = grpc.insecure_channel(
        '43.201.26.161:8088',
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
                store_id="5fjVwE8z",
                inquiry_type="inquiry",
                num=1
            )
            yield request

            # 30fps에 맞춰 대기
            time.sleep(1/30)

    # gRPC 요청 전송 (하나의 스트림으로)
    try:
        response = stub.FrameToMarkingData(frame_iterator())
        
        print("📦 전체 응답 내용 (raw proto object):")
        print(response)

        # ✅ JSON 형식으로 보기 (기본값도 포함)
        print("\n📦 전체 응답 내용 (JSON 형식):")
        json_str = MessageToJson(
            response,
            including_default_value_fields=True,  # success: false 같은 기본값도 출력됨
            preserving_proto_field_name=True      # proto 정의 그대로 필드 이름 유지
        )
        print(json_str)

        # ✅ 개별 필드 접근해서 출력
        print("\n📋 응답 필드별 출력:")
        print(f"▶ success: {getattr(response, 'success', '없음')}")
        print(f"▶ error: {response.error} ({error_pb2.EError.Name(response.error)})")

        # 필요 시 다른 필드도 여기에 추가
        # 예: print(f"▶ message: {getattr(response, 'message', '없음')}")

    except grpc.RpcError as e:
        print(f"🚨 gRPC 에러 발생: {e}")
        print(f"▶ status code: {e.code()}")
        print(f"▶ details: {e.details()}")
    except Exception as e:
        print(f"🚨 일반 예외 발생: {e}")

    cap.release()

if __name__ == "__main__":
    video_path = "오류.mp4"
    test_frame_to_marking_data(video_path)