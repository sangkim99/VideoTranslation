from fastapi import FastAPI
import grpc
import os
import numpy as np
import mediapipe as mp
import cv2
import time
import threading
import uvicorn
from dotenv import load_dotenv
from concurrent import futures
import traceback

# proto import
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'gen'))
from gen import middleware_pb2
from gen import middleware_pb2_grpc
from gen import service_pb2
from gen import service_pb2_grpc
from gen import error_pb2
from gen import inquiry_pb2

# 환경변수 또는 고정 값
load_dotenv()
MIDDLEWARE_HOST = "localhost:8080"
API_HOST = "3.34.190.174:50051"

app = FastAPI()

# Mediapipe 초기화
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=2)

def compute_angles(joints_63):
    joints = joints_63.reshape(-1, 21, 3)
    seq_out = []

    for joint in joints:
        v1 = joint[[0,1,2,3,0,5,6,7,0,9,10,11,0,13,14,15,0,17,18,19], :]
        v2 = joint[[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], :]
        v = v2 - v1
        v = v / np.linalg.norm(v, axis=1, keepdims=True)

        angle = np.arccos(np.einsum('nt,nt->n',
            v[[0,1,2,4,5,6,8,9,10,12,13,14,16,17,18],:], 
            v[[1,2,3,5,6,7,9,10,11,13,14,15,17,18,19],:]
        ))
        angle = np.degrees(angle)
        feature = np.concatenate([joint.flatten(), angle])
        seq_out.append(feature)

    return np.array(seq_out)

def process_frame_to_coordinates(frame_bytes):
    try:
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            print("❌ 프레임 디코딩 실패")
            return [0.0] * 78

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(img_rgb)

        if result.multi_hand_landmarks:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 손 감지 성공")
            for res in result.multi_hand_landmarks:
                joint = np.zeros((21, 3))
                for j, lm in enumerate(res.landmark):
                    joint[j] = [lm.x, lm.y, lm.z]
                joints_np = np.array([joint.flatten()])
                angles = compute_angles(joints_np)
                return angles.flatten().tolist()
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 손 감지 실패")
            return [0.0] * 78
    except Exception as e:
        print(f"[프레임 처리 오류] {e}")
        traceback.print_exc()
        return [0.0] * 78

class ChangeMiddlwareServicer(middleware_pb2_grpc.ChangeMiddlwareServicer):
    def __init__(self):
        self.api_channel = grpc.insecure_channel(
            API_HOST,
            options=[
                ('grpc.max_send_message_length', 10 * 1024 * 1024),
                ('grpc.max_receive_message_length', 10 * 1024 * 1024)
            ]
        )
        self.api_stub = service_pb2_grpc.APIServiceStub(self.api_channel)

    def FrameToMarkingData(self, request_iterator, context):
        try:
            def request_gen():
                for request in request_iterator:
                    print("🟢 프레임 수신")
                    coordinates = process_frame_to_coordinates(request.frame[0])
                    yield inquiry_pb2.InquiryRequest(
                        store_code=request.store_id,
                        frame_data=coordinates,
                        inquiry_type=request.inquiry_type,
                        num=request.num
                    )

            response = self.api_stub.StreamInquiries(request_gen())
            return middleware_pb2.FrameToMarkingDataResposne(
                success=response.success,
                error=response.error
            )
        except Exception as e:
            print(f"[gRPC 처리 오류] {e}")
            traceback.print_exc()
            return middleware_pb2.FrameToMarkingDataResposne(
                success=False,
                error=error_pb2.EError.EE_API_FAILED
            )

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    middleware_pb2_grpc.add_ChangeMiddlwareServicer_to_server(
        ChangeMiddlwareServicer(), server
    )
    server.add_insecure_port('0.0.0.0:8088')
    print("🟢 gRPC 서버 시작 (0.0.0.0:8088)")
    server.start()
    server.wait_for_termination()

def serve_fastapi():
    print("🟢 FastAPI 서버 시작 (0.0.0.0:8000)")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == '__main__':
    grpc_thread = threading.Thread(target=serve_grpc)
    grpc_thread.start()

    serve_fastapi()
