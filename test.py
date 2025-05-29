import cv2
import grpc
import numpy as np
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

    fps = 30  # 강제로 30fps 기준으로 전송
    frame_interval = 1.0 / fps
    frame_count = 0

    def frame_iterator():
        nonlocal frame_count
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            frame_count += 1
            print(f"📤 {frame_count}번째 프레임 전송")

            request = middleware_pb2.FrameToMarkingDataRequest(
                frame=[frame_bytes],
                store_id="5fjVwE8z",
                inquiry_type="inquiry",
                num=frame_count
            )
            yield request

            time.sleep(frame_interval)  # 정확히 1초에 30프레임 전송되도록 간격 유지

        print(f"\n✅ 총 전송된 프레임 수: {frame_count}")

    try:
        response = stub.FrameToMarkingData(frame_iterator())

        print("\n📦 전체 응답 내용 (JSON 형식):")
        json_str = MessageToJson(
            response,
            including_default_value_fields=True,
            preserving_proto_field_name=True
        )
        print(json_str)

        print("\n📋 응답 필드별 출력:")
        print(f"▶ success: {getattr(response, 'success', '없음')}")
        print(f"▶ error: {response.error} ({error_pb2.EError.Name(response.error)})")

    except grpc.RpcError as e:
        print(f"🚨 gRPC 에러 발생: {e}")
        print(f"▶ status code: {e.code()}")
        print(f"▶ details: {e.details()}")
    except Exception as e:
        print(f"🚨 일반 예외 발생: {e}")
    finally:
        cap.release()

if __name__ == "__main__":
    video_path = "아메리카노.mp4"  # 실제 파일명 입력
    test_frame_to_marking_data(video_path)
