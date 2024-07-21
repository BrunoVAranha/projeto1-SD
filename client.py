import grpc
import message_pb2
import message_pb2_grpc
import time

def listen_unary(stub):
    channel = "canal1"
    try:
        while True:
            response = stub.ReceiveMessage(message_pb2.ChannelRequest(channel=channel))
            print(f"Received message: {response.message}")
            time.sleep(1)  # Sleep for a short duration before checking again
    except grpc.RpcError as e:
        print(f"Error receiving messages: {e}")

def stream_messages(stub):
    channel = "canal2"
    try:
        responses = stub.StreamMessages(message_pb2.ChannelRequest(channel=channel))
        for response in responses:
            print(f"Received message: {response.message}")
    except grpc.RpcError as e:
        print(f"Error streaming messages: {e}")

def run():
    choice = input("Choose channel - 1 for canal1 (Unary RPC), 2 for canal2 (Server Streaming RPC): ")
    with grpc.insecure_channel('localhost:50051') as grpc_channel:
        stub = message_pb2_grpc.MessengerStub(grpc_channel)
        if choice == '1':
            print(f"Client connected to server and listening for messages on canal1...")
            listen_unary(stub)
        elif choice == '2':
            print(f"Client connected to server and listening for messages on canal2...")
            stream_messages(stub)
        else:
            print("Invalid choice")

if __name__ == '__main__':
    run()