import grpc
from concurrent import futures
import time
import threading
import queue

import message_pb2
import message_pb2_grpc

class MessengerServicer(message_pb2_grpc.MessengerServicer):
    def __init__(self):
        self.channels = {
            "canal1": queue.Queue(),  # Single queue for Unary RPC
            "canal2": []  # List of queues for Server Streaming RPC
        }
        self.lock = threading.Lock()

    def ReceiveMessage(self, request, context):
        channel = request.channel
        if channel != "canal1":
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid channel specified.")
        while True:
            try:
                message = self.channels[channel].get(timeout=5)
                return message_pb2.MessageResponse(message=message)
            except queue.Empty:
                if context.is_active():
                    continue
                else:
                    context.abort(grpc.StatusCode.CANCELLED, "Client disconnected")

    def StreamMessages(self, request, context):
        channel = request.channel
        if channel != "canal2":
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid channel specified.")
        q = queue.Queue()
        with self.lock:
            self.channels[channel].append(q)
        try:
            while True:
                message = q.get()
                response = message_pb2.MessageResponse(message=message)
                yield response
        except grpc.RpcError as e:
            print(f"Client disconnected: {e}")
            with self.lock:
                self.channels[channel].remove(q)

    def broadcast_message(self, channel, message):
        with self.lock:
            if channel == "canal2":
                for client in self.channels[channel]:
                    client.put(message)
            elif channel == "canal1":
                self.channels[channel].put(message)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = MessengerServicer()
    message_pb2_grpc.add_MessengerServicer_to_server(servicer, server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")

    def input_thread():
        while True:
            channel = input("Enter channel (canal1 or canal2): ")
            if channel not in ['canal1', 'canal2']:
                print("Invalid channel. Please enter 'canal1' or 'canal2'.")
                continue
            message = input("Enter message to send to clients: ")
            servicer.broadcast_message(channel, message)

    thread = threading.Thread(target=input_thread, daemon=True)
    thread.start()

    try:
        while True:
            time.sleep(86400)  # one day in seconds
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
