from fastapi import FastAPI
import grpc
import os
import numpy as np
import mediapipe as mp
import json
from dotenv import load_dotenv
import base64
import asyncio
from typing import AsyncGenerator
from concurrent import futures
import cv2
import time

# proto 파일 import
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'gen'))
from gen import middleware_pb2
from gen import middleware_pb2_grpc
from gen import service_pb2
from gen import service_pb2_grpc
from gen import error_pb2
from gen import inquiry_pb2

app = FastAPI()

# 환경 변수 설정
load_dotenv()
#MIDDLEWARE_HOST = os.getenv("MIDDLEWARE_HOST")
MIDDLEWARE_HOST = "localhost:8080"
#API_HOST = os.getenv("API_HOST")
API_HOST = "3.34.190.174:50051"

# gRPC 채널 설정
middleware_channel = grpc.insecure_channel(
    MIDDLEWARE_HOST,
    options=[
        ('grpc.max_send_message_length', 10 * 1024 * 1024),
        ('grpc.max_receive_message_length', 10 * 1024 * 1024)
    ]
)

api_channel = grpc.insecure_channel(
    API_HOST,
    options=[
        ('grpc.max_send_message_length', 10 * 1024 * 1024),
        ('grpc.max_receive_message_length', 10 * 1024 * 1024)
    ]
)

# gRPC 스텁 생성
middleware_stub = middleware_pb2_grpc.ChangeMiddlwareStub(middleware_channel)
api_stub = service_pb2_grpc.APIServiceStub(api_channel)

# Mediapipe 초기화
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,  # 단일 프레임 처리이므로 True로 설정
    max_num_hands=2
)

def compute_angles(joints_63):
    joints = joints_63.reshape(-1, 21, 3)
    seq_out = []

    for joint in joints:
        v1 = joint[[0,1,2,3,0,5,6,7,0,9,10,11,0,13,14,15,0,17,18,19], :]
        v2 = joint[[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], :]
        v = v2 - v1
        v = v / np.linalg.norm(v, axis=1)[:, np.newaxis]

        angle = np.arccos(np.einsum('nt,nt->n',
            v[[0,1,2,4,5,6,8,9,10,12,13,14,16,17,18],:], 
            v[[1,2,3,5,6,7,9,10,11,13,14,15,17,18,19],:]
        ))
        angle = np.degrees(angle)
        feature = np.concatenate([joint.flatten(), angle])
        seq_out.append(feature)

    return np.array(seq_out)

def process_frame_to_coordinates(frame_bytes):
    """
    프레임 바이트 데이터에서 손 좌표를 추출하는 함수
    """
    # 바이트 데이터를 numpy 배열로 변환
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # BGR -> RGB 변환
    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(img_rgb)

    if result.multi_hand_landmarks:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 손 감지 성공")
        for res in result.multi_hand_landmarks:
            joint = np.zeros((21, 3))
            for j, lm in enumerate(res.landmark):
                joint[j] = [lm.x, lm.y, lm.z]

            # 각도 계산
            joints_np = np.array([joint.flatten()])
            angles = compute_angles(joints_np)
            flat_joints = angles.flatten().tolist()
            return flat_joints
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 손 감지 실패")
        # 손이 감지되지 않으면 더미 데이터 반환
        return [0.0] * 78

async def process_frame_stream(request_iterator):
    """
    프레임 스트림을 처리하는 함수
    """
    try:
        # API 서버로 스트림 요청 생성
        api_request_iterator = create_api_request_iterator(request_iterator)
        
        # API 서버로 스트림 전송 및 응답 수신
        for response in api_stub.StreamInquiries(api_request_iterator):
            yield response
            
    except Exception as e:
        yield {"error": str(e)}

async def create_api_request_iterator(request_iterator):
    """
    API 서버로 전송할 요청 스트림 생성
    """
    for request in request_iterator:
        try:
            print("1. 새로운 프레임 수신")
            # 프레임에서 좌표 추출 (손이 감지되지 않으면 더미 데이터 반환)
            coordinates = process_frame_to_coordinates(request.frame[0])
        except Exception as e:
            print(f"오류: {e}")
            coordinates = [0.0] * 78
        
        # API 서버 요청 생성
        api_request = inquiry_pb2.InquiryRequest(
            store_code=request.store_id,
            frame_data=coordinates,
            inquiry_type=request.inquiry_type,
            num=request.num
        )
        yield api_request

class ChangeMiddlwareServicer(middleware_pb2_grpc.ChangeMiddlwareServicer):
    def __init__(self):
        # API 서버 연결
        self.api_channel = grpc.insecure_channel(
            API_HOST,
            options=[
                ('grpc.max_send_message_length', 10 * 1024 * 1024),
                ('grpc.max_receive_message_length', 10 * 1024 * 1024)
            ]
        )
        self.api_stub = service_pb2_grpc.APIServiceStub(self.api_channel)
        
        # Mediapipe 초기화
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=True, max_num_hands=2)

    def FrameToMarkingData(self, request_iterator, context):
        try:
            # API 서버로 보낼 요청 스트림 생성
            api_request_iterator = self.create_api_request_iterator(request_iterator)
            
            # 하나의 스트림으로 모든 프레임 처리
            response = self.api_stub.StreamInquiries(api_request_iterator)
            return middleware_pb2.FrameToMarkingDataResposne(
                success=response.success,
                error=response.error
            )
                
        except Exception as e:
            print(f"오류: {e}")
            return middleware_pb2.FrameToMarkingDataResposne(
                success=False,
                error=error_pb2.EError.EE_API_FAILED
            )

    def create_api_request_iterator(self, request_iterator):
        """
        API 서버로 전송할 요청 스트림 생성
        """
        for request in request_iterator:
            print("1. 새로운 프레임 수신")
            # 프레임에서 좌표 추출 (손이 감지되지 않으면 더미 데이터 반환)
            coordinates = process_frame_to_coordinates(request.frame[0])
            
            # API 서버 요청 생성
            api_request = inquiry_pb2.InquiryRequest(
                store_code=request.store_id,
                frame_data=coordinates,
                inquiry_type=request.inquiry_type,
                num=request.num
            )
            yield api_request

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    middleware_pb2_grpc.add_ChangeMiddlwareServicer_to_server(
        ChangeMiddlwareServicer(), server
    )
    server.add_insecure_port('0.0.0.0:8088')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()