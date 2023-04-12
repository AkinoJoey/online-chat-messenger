import socket
import asyncio
import _thread
import random
import re

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '127.0.0.1'
        self.port = 9005
        self.chatrooms = {} # String room_name: Chatroom chat_room
     
    def accept(self):
        print("Starting up on {} port {}".format(self.address,self.port))

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        self.sock.listen(128)
        
        while True:
            connection, client_address = self.sock.accept()
            _thread.start_new_thread(self.get_user_data,(connection, client_address))
    
    def get_user_data(self, connection, client_address):
        try:
            print('connection from', client_address)
            SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE  = 2
            
            user_name = self.convert_user_data_to_string(connection, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            print("Username: {}".format(user_name))
            
            service_type = self.convert_user_data_to_string(connection, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            make_new_room = "1"
            string_of_service = "make a new room" if service_type == make_new_room else "join in a room"
            print("Service Type: {}".format(string_of_service))   
            
            chatroom_name = self.prompt_chatroom_name(connection,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE,service_type)
            print("Chat room name is {}".format(chatroom_name))
            
            max_member = self.convert_user_data_to_string(connection, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            
            print("User adress: {}".format(client_address))
            
            user_address = client_address[0]
            user_port = client_address[1]
            
            self.send_port_number(connection, user_port,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            chat_client = self.make_chat_client(user_name, user_address,user_port,service_type)
            
            if service_type == make_new_room:
                chatroom_port = random.randint(2000, 65500)
                self.send_port_number(connection,chatroom_port,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
                
                new_chatroom = self.make_chatroom(chatroom_port,chatroom_name, max_member, chat_client)
                self.chatrooms[new_chatroom.room_name] = new_chatroom
                new_chatroom.start_chat()
                
            else:
                chatroom_port = self.chatrooms[chatroom_name].port
                self.send_port_number(connection,chatroom_port,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
                self.add_client_to_chatroom(chat_client, chatroom_name)
                
        except Exception as e:
            print('Error: ' + str(e))
    
    def convert_user_data_to_string(self,connection,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE):
        userdata_length = int.from_bytes(connection.recv(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE), "big")
        userdata_string = connection.recv(userdata_length).decode("utf-8")
        return userdata_string
            
    def prompt_chatroom_name(self,connection, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, service_type):
        while True:
            chatroom_name = self.convert_user_data_to_string(connection, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            make_new_room = "1"
            ask_back = 0
            no_problem = 1
            
            self.delete_empty_chatroom()
            
            if service_type == make_new_room:
                if chatroom_name not in self.chatrooms:
                    connection.sendall((no_problem).to_bytes(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, "big"))
                    return chatroom_name
                else:
                    connection.sendall((ask_back).to_bytes(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, "big"))
                    
            else:
                if chatroom_name in self.chatrooms and self.check_chat_room_capacity(chatroom_name) == True:
                    connection.sendall((no_problem).to_bytes(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, "big"))
                    return chatroom_name
                else:
                    connection.sendall((ask_back).to_bytes(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, "big"))
        
    def make_chat_client(self ,user_name, address, port, service_type):
        status = "host" if service_type == "1" else "participant"
        return ChatClient(user_name, address, port, status)
    
    def send_port_number(self,connection,port,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE):
        connection.sendall(port.to_bytes(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, "big"))
    
    def make_chatroom(self,chatroom_port,room_name, max_member, client):
        return ChatRoom(chatroom_port, room_name, max_member, client)
    
    def add_client_to_chatroom(self, client, room_name):
        chatroom = self.chatrooms[room_name]
        chatroom.participants[client.address + str(client.port)] = client
    
    def delete_empty_chatroom(self):
        for room_name in list(self.chatrooms.keys()):
            chatroom = self.chatrooms[room_name]
            if len(chatroom.participants) < 1:
                del self.chatrooms[room_name]
        
    def check_chat_room_capacity(self,room_name):
        chatroom = self.chatrooms[room_name]
        return len(chatroom.participants) < int(chatroom.max_member)
    
class ChatClient:
    def __init__(self, user_name, address, port,status):
        self.user_name = user_name
        self.address = address
        self.port = port
        self.status = status
        
class ChatRoom:
    def __init__(self,port, room_name, max_member, client):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.address = '127.0.0.1'
        self.port = port
        self.room_name = room_name
        self.max_member = max_member
        self.participants = {(client.address) + str(client.port): client}
        self.hostMap = {(client.address) + str(client.port): client}
    
    def start_chat(self):
        print('\nStart the new chat room "{}"'.format(self.room_name))
        self.sock.bind((self.address, self.port))

        try:
            asyncio.run(self.receve_data())

        except Exception as e:
            print("Error: " + str(e))
            self.sock.close()
        
        finally:
            self.sock.close()
    
    async def receve_data(self):
        while self.exist_participants():
            loop = asyncio.get_event_loop()
            data, address = await loop.sock_recvfrom(self.sock, 4096)
            sender = self.participants[address[0] + str(address[1])]

            if data:
                message = self.extract_message(data)
                if message == "real-Bye-Bye":
                    await self.delete_participant(address)
                else:    
                    messageToSend = "{}: {}".format(sender.user_name, message)
                    print(messageToSend)   
                    await self.send_message(messageToSend,sender)  
          
            await asyncio.sleep(0.1)
            
    def exist_participants(self):
        return len(self.participants) >= 1
    
    def extract_message(self, data):
        data = data.decode("utf-8")
        
        # チャットルームに参加する場合、クライアントが最初に送るメッセージ：　{roomname}:join
        if data == "{}:join".format(self.room_name):
            return "join"
        else:
            # クライアントがサーバーに送信するメッセージのプレフィックス：{roomname}:{message-size}:{message}
            extract_message_pattern = self.room_name + ":" + r'[0-9]*' + ":"
            return re.split(extract_message_pattern, data)[1]
    
    async def delete_participant(self, address):
        key = address[0] + str(address[1])
        target = self.participants[key]
        del self.participants[key]
        
        if self.exist_participants() == True:
            announce = "Server: {} left the room.".format(target.user_name)
            await self.announce_from_server(announce)
        else:
            print("{} has been closed.".format(self.room_name))
            self.sock.close()
    
    async def send_message(self,message,sender):
        loop = asyncio.get_event_loop()
        
        for client in self.participants.values():
            if sender != client:
                await loop.sock_sendto(self.sock, message.encode("utf-8"), (client.address, client.port))
        
        await asyncio.sleep(0.1)
    
    async def announce_from_server(self, message):
        loop = asyncio.get_event_loop()

        for client in self.participants.values():
            await loop.sock_sendto(self.sock, message.encode("utf-8"), (client.address, client.port))
        
        await asyncio.sleep(0.1)
        
class Main:
    server = Server()
    server.accept()
    
if __name__ == "__main__":
    Main()