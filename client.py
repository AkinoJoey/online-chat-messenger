import socket
import sys
import asyncio
import aioconsole

class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '127.0.0.1'
        self.port = None
        self.status = None
        self.server_address = '127.0.0.1'
        self.server_port = 9005
    
    def connect_server(self):
        try:
            self.sock.settimeout(2)
            self.sock.connect((self.server_address,self.server_port))
            
        except OSError as e:
            print(e)
            sys.exit(1)
        
        try:
            SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE  = 2
            
            user_name = input("--> Type in your name: ")
            self.send_user_data(user_name, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            
            service_type = self.prompt_service_type()
            self.send_user_data(service_type,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            self.set_status(service_type)
            
            chatroom_name = self.prompt_chat_room_name(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
                
            # ユーザーが参加者のときはmaxMemberを0に設定しておく
            max_member = "0" if service_type == "2" else self.prompt_max_member()
            self.send_user_data(max_member,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            
            self.set_client_port_number(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)

            chatroom_port =  self.get_chatroom_port(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            self.make_chat_client(chatroom_name, chatroom_port)
            
        except Exception as e:
            print(e)
            
        finally:
            print('closing chat service')
            self.sock.close()
    
    def send_user_data(self, userdata, SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE):
        userdata_bytes = userdata.encode("utf-8")
        self.sock.send(len(userdata_bytes).to_bytes(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE, "big"))
        self.sock.send(userdata_bytes)

    def prompt_service_type(self):
        while True:
            service_type = input("--> Type in 1 if you want to make a new chat room. Type in 2 if you want to join in a chat room: ")
            if service_type == "1" or service_type == "2":
                return service_type
            else:
                print("Please type in 1 or 2")
    
    def set_status(self,service_type):
        if service_type == "1":
            self.status = "host"
            
        else:
            self.status = "participant"
    
    def prompt_chat_room_name(self,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE):
        while True:
            print(self.status)
            chatroom_name = input("--> Type in the name of the chat room you want to make: ") if self.status == "host" else input("--> Type in the name of the chat room you want to join in: ")
            self.send_user_data(chatroom_name,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE)
            
            find_chatroom = int.from_bytes(self.sock.recv(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE), "big")
            
            if find_chatroom == 0:
                if self.status == "host":
                    print("The chat room name is already in use.")
                else:
                    print("You cannot join the chat room. It does not exist or is already full.")
            else:
                return chatroom_name
    
    def prompt_max_member(self):
        while True:
            max_member = input("--> Type in the maximum number of participants for your chat room: ")
            if max_member.isdigit() and max_member != "0":
                return max_member
            else:
                print("Please type in a natural number.")
        
    def set_client_port_number(self,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE):
        while self.port == None:
            self.port = int.from_bytes(self.sock.recv(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE), "big")     
    
    def get_chatroom_port(self,SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE):
        chatroom_port = None
        while True:
            chatroom_port = int.from_bytes(self.sock.recv(SIZE_OF_DATA_SEND_AND_RECEIVE_PER_ONCE), "big")

            if chatroom_port != None:
                return chatroom_port
    
    def make_chat_client(self,chatroom_name, chatroom_port):
        chatClient = ChatClient(self.port,self.status,chatroom_name,chatroom_port)

class ChatClient:
    def __init__(self,port,status,chatroom_name,chatroom_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.address = '127.0.0.1'
        self.port = port
        self.status = status
        self.chatroom_address = '127.0.0.1'
        self.chatroom_port = chatroom_port
        self.chatroom_name = chatroom_name
        self.sock.bind((self.address, self.port))

        print('\nStart the new chat room "{}"'.format(self.chatroom_name)) if self.status == "host" else print("Join in {}".format(self.chatroom_name))
        
        if self.status == "participant":
            join_message = "{}:join".format(self.chatroom_name)
            self.sock.sendto(join_message.encode("utf-8"),(self.chatroom_address, self.chatroom_port))
        
        asyncio.run(self.start_chat(),debug=True)

    async def start_chat(self):
        try: 
            async with asyncio.TaskGroup() as tg:
                receve_task = tg.create_task(self.receve_message())
                send_task = tg.create_task(self.send_message(receve_task))
            
        except Exception as e:
            print("Error: " + str(e))
            self.sock.close()
            
        finally:
            self.sock.close()

    async def receve_message(self):
        while True:
            loop = asyncio.get_running_loop()
            data, address = await loop.sock_recvfrom(self.sock, 4096)
            
            if data:
                print(data.decode())    

            await asyncio.sleep(0.1)
    
    async def send_message(self,receve_task):
        while True:
            message = await aioconsole.ainput()
            leave = False

            if message == "bye":
                leave = await self.confirm_leave_chatroom()

            if leave == True:
                await self.leave_chatroom(receve_task)
                break
            else:
                message_size = len(message)
                prefix = "{}:{}:{}".format(self.chatroom_name, message_size, message)
                loop = asyncio.get_running_loop()
                await loop.sock_sendto(self.sock, prefix.encode("utf-8"), (self.chatroom_address, self.chatroom_port))
                print()
                print("\nYou: {}".format(message))
            
            await asyncio.sleep(0.1)
    
    async def confirm_leave_chatroom(self):
        while True:
            confirm_message = await aioconsole.ainput("--> Do you want to leave the chat room? Type in Yes or No: ")
            if confirm_message == "Yes":
                return True
            elif confirm_message == "No":
                return False
            else:
                confirm_message = print("Please tyep in Yes or No")
    
    async def leave_chatroom(self,receve_task):
        receve_task.cancel()
        string_to_leave = "real-Bye-Bye"
        message_size = len(string_to_leave)
        prefix = "{}:{}:{}".format(self.chatroom_name, message_size, string_to_leave)
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(self.sock, prefix.encode("utf-8"), (self.chatroom_address, self.chatroom_port))
        
class Main:
    client = Client()
    client.connect_server()
    
if __name__ == '__main__':
    Main()

