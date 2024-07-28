import grpc
from concurrent import futures
import threading
import queue
import time
import message_pb2
import message_pb2_grpc

class MessengerServicer(message_pb2_grpc.MessengerServicer):
    def __init__(self):
        self.channels = {}
        self.channel_types = {}
        self.lock = threading.Lock()

    def create_channel(self, name, channel_type):
        with self.lock:
            if name in self.channels:
                print(f"Canal {name} já existe.")
                return
            if channel_type == message_pb2.UNARY:
                self.channels[name] = queue.Queue()
                self.channel_types[name] = message_pb2.UNARY
            elif channel_type == message_pb2.STREAMING:
                self.channels[name] = []
                self.channel_types[name] = message_pb2.STREAMING
            else:
                print("Tipo de canal inválido. Por favor, insira 0 para UNARY ou 1 para STREAMING.")
                return
            print(f"Canal {name} do tipo {channel_type} criado.")

    def GetChannels(self, request, context):
        with self.lock:
            return message_pb2.ChannelList(channels=list(self.channels.keys()))

    def GetChannelInfo(self, request, context):
        channel = request.channel
        with self.lock:
            if channel not in self.channels:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Canal não encontrado.")
            return message_pb2.ChannelInfo(name=channel, type=self.channel_types[channel])

    def ReceiveMessage(self, request, context):
        channel = request.channel
        if channel not in self.channels or self.channel_types[channel] != message_pb2.UNARY:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Canal inválido ou não-unário especificado.")
        while True:
            try:
                message = self.channels[channel].get(timeout=1)
                return message_pb2.MessageResponse(message=message)
            except queue.Empty:
                if not context.is_active():
                    context.abort(grpc.StatusCode.CANCELLED, "Cliente desconectado")
                continue

    def StreamMessages(self, request, context):
        channel = request.channel
        if channel not in self.channels or self.channel_types[channel] != message_pb2.STREAMING:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Canal inválido ou não-streaming especificado.")
        q = queue.Queue()
        with self.lock:
            self.channels[channel].append(q)
        try:
            while True:
                message = q.get()
                response = message_pb2.MessageResponse(message=message)
                yield response
        except grpc.RpcError as e:
            print(f"Cliente desconectado: {e}")
            with self.lock:
                self.channels[channel].remove(q)

    def PostMessage(self, request, context):
        channel = request.channel
        message = request.message
        with self.lock:
            if channel not in self.channels:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Canal não encontrado.")
            if self.channel_types[channel] == message_pb2.UNARY:
                self.channels[channel].put(message)
            elif self.channel_types[channel] == message_pb2.STREAMING:
                for client in self.channels[channel]:
                    client.put(message)
        return message_pb2.Empty()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = MessengerServicer()
    message_pb2_grpc.add_MessengerServicer_to_server(servicer, server)
    server.add_insecure_port('[::]:50000')
    server.start()
    print("Servidor iniciado na porta 50000")

    def input_thread():
        while True:
            action = input("Digite a ação (create): ")
            if action == "create":
                channel_name = input("Digite o nome do canal: ")
                channel_type = int(input("Digite o tipo de canal (0 para UNARY, 1 para STREAMING): "))
                servicer.create_channel(channel_name, channel_type)
            else:
                print("Ação inválida. Por favor, digite 'create'.")

    thread = threading.Thread(target=input_thread, daemon=True)
    thread.start()

    try:
        while True:
            time.sleep(99999)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()